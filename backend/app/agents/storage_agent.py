import asyncio
import json
import logging
import mimetypes
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.enums import ContentStatus
from app.core.interfaces import ObjectStorage
from app.core.types import ContentDraft, LLMResponse, MediaBundle, ProjectContext, StoredObject, TrendCandidate
from app.models import Asset, Content, Project
from app.repositories.assets import AssetRepository
from app.repositories.contents import ContentRepository
from app.repositories.projects import ProjectRepository
from app.repositories.topics import TopicRepository

logger = logging.getLogger("app.pipeline")


@dataclass(frozen=True, slots=True)
class Job:
    content_id: UUID
    status: str
    project: ProjectContext
    topic: str
    keywords: list[str]
    draft: ContentDraft | None
    part: int = 1
    instructions: bool = False  # el tema es un texto del propio usuario (Mi idea): se sigue al pie de la letra
    previous: str = ""  # guiones de las partes anteriores de la serie


def _context(p: Project) -> ProjectContext:
    return ProjectContext(id=p.id, name=p.name, niche=p.niche, language=p.language, config=p.config or {})


def _with_summary(topic) -> str:
    """El guionista recibe el titular y, si la fuente lo dio, su resumen. Las ideas del usuario van tal cual."""
    return f"{topic.topic}. {topic.summary}" if topic.summary and topic.source != "idea" else topic.topic


class StorageAgent:
    """Único agente que escribe en PostgreSQL y R2 y que mueve contents.status. Cada operación usa su propia
    transacción corta: nunca se mantiene una conexión abierta mientras se genera media."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], storage: ObjectStorage):
        self._sf = session_factory
        self._storage = storage

    # --- cola y proyectos ---
    async def active_projects(self, project_ids: Sequence[UUID] | None = None) -> list[ProjectContext]:
        async with self._sf() as s:
            projects = await ProjectRepository(s).find_active()
        return [_context(p) for p in projects if not project_ids or p.id in project_ids]

    async def queue(self, limit: int, project_ids: Sequence[UUID] | None = None) -> list[UUID]:
        async with self._sf() as s:
            return list(await ContentRepository(s).find_queue(project_ids, limit))

    async def load_job(self, content_id: UUID) -> Job:
        async with self._sf() as s:
            content = await ContentRepository(s).get(content_id)
            if content is None:
                raise LookupError(f"contenido {content_id} no existe")
            project = await ProjectRepository(s).get(content.project_id)
            earlier = await ContentRepository(s).previous_scripts(content_id) if content.parent_id else []
            topic = await TopicRepository(s).get(content.topic_id) if content.topic_id else None
        # 'guion' sin guion es un estado incoherente: se rehace desde el LLM
        has_script = content.status == ContentStatus.GUION and bool(content.script)
        draft = ContentDraft(content.title, content.hook, content.script, content.caption, content.hashtags, content.cta)
        return Job(
            content_id=content.id, status="guion" if has_script else "idea", project=_context(project),
            topic=_with_summary(topic) if topic else content.title, keywords=topic.keywords if topic else [],
            draft=draft if has_script else None, part=content.part,
            instructions=bool(topic and topic.source == "idea"),
            previous="\n\n".join(f"PARTE {n} — {title}\n{script}" for n, title, script in earlier),
        )

    # --- tendencias ---
    async def has_unused_topic(self, project_id: UUID) -> bool:
        async with self._sf() as s:
            return await TopicRepository(s).next_unused(project_id) is not None

    async def save_topics(self, project_id: UUID, candidates: Sequence[TrendCandidate]) -> int:
        async with self._sf() as s:
            added = await TopicRepository(s).add_new(project_id, candidates)
            await s.commit()
        return added

    async def open_idea(self, project_id: UUID) -> tuple[UUID, str, list[str]] | None:
        """Convierte el mejor tema sin usar en un contenido en estado 'idea'."""
        async with self._sf() as s:
            topic = await TopicRepository(s).next_unused(project_id)
            if topic is None:
                return None
            content = await ContentRepository(s).save(Content(project_id=project_id, topic_id=topic.id))
            await s.commit()
        return content.id, _with_summary(topic), topic.keywords

    # --- avance del flujo ---
    async def save_draft(self, content_id: UUID, draft: ContentDraft, llm: LLMResponse) -> None:
        """idea → guion. Se guarda antes de generar media: un fallo posterior no desperdicia la llamada al LLM."""
        async with self._sf() as s:
            repo = ContentRepository(s)
            content = await repo.get(content_id)
            content.title, content.hook, content.script = draft.title, draft.hook, draft.script
            content.caption, content.hashtags, content.cta = draft.caption, draft.hashtags, draft.cta
            content.llm_provider, content.model_name = llm.provider, llm.model
            content.tokens_used += llm.tokens_used
            content.last_error = ""
            content.status = ContentStatus.GUION.value
            await repo.save(content)
            await s.commit()

    async def save_media(self, content_id: UUID, bundle: MediaBundle, topic: str) -> None:
        """Sube los artefactos a R2, reemplaza los assets y pasa guion → generado."""
        async with self._sf() as s:
            content = await ContentRepository(s).get(content_id)
            old_keys = {a.storage_key for a in await AssetRepository(s).find_for_content(content_id)}

        prefix = f"contents/{content_id}"
        metadata = {
            "topic": topic, "title": content.title, "duration": round(bundle.video.duration, 2),
            "status": ContentStatus.GENERADO.value, "created_at": content.created_at.isoformat(),
        }
        uploads = [
            self._storage.put_file(f"{prefix}/video.mp4", bundle.video.path, "video/mp4"),
            self._storage.put_bytes(f"{prefix}/caption.txt", content.caption.encode(), "text/plain; charset=utf-8"),
            self._storage.put_bytes(f"{prefix}/hashtags.txt", " ".join(content.hashtags).encode(), "text/plain; charset=utf-8"),
            self._storage.put_bytes(f"{prefix}/metadata.json", json.dumps(metadata, ensure_ascii=False).encode(), "application/json"),
            self._storage.put_bytes(f"{prefix}/subtitles.srt", bundle.subtitles.encode(), "application/x-subrip"),
            *(self._image(prefix, i, path) for i, path in enumerate(bundle.images)),
        ]
        stored: list[StoredObject] = await asyncio.gather(*uploads)
        kinds = ["video", "caption", "hashtags", "metadata", "subtitles", *["image"] * len(bundle.images)]

        async with self._sf() as s:
            await AssetRepository(s).replace_for_content(content_id, [
                Asset(content_id=content_id, kind=kind, storage_provider=o.provider, storage_key=o.key,
                      file_size=o.file_size, mime_type=o.mime_type)
                for kind, o in zip(kinds, stored)
            ])
            repo = ContentRepository(s)
            content = await repo.get(content_id)
            content.status = ContentStatus.GENERADO.value
            content.last_error = ""
            content.duration_seconds = round(bundle.video.duration, 2)
            await repo.save(content)
            await s.commit()

        # Regenerar con menos imágenes dejaría huérfanas las antiguas en R2 (consumen cuota de almacenamiento).
        for key in old_keys - {o.key for o in stored}:
            try:
                await self._storage.delete(key)
            except Exception:
                logger.warning("stale asset not deleted", extra={"fields": {"key": key}})

    async def mark_failed(self, content_id: UUID, error: str) -> None:
        """Registra el fallo y saca el contenido de la cola hasta que el usuario lo reintente desde el portal.
        El estado no cambia: 'idea' repite el LLM, 'guion' solo la media."""
        async with self._sf() as s:
            await ContentRepository(s).mark_failed(content_id, error)
            await s.commit()

    def _image(self, prefix: str, index: int, path: Path):
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        return self._storage.put_file(f"{prefix}/images/img_{index}{path.suffix}", path, mime)
