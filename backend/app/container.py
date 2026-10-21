"""Único sitio que conoce las implementaciones concretas. Cambiar de proveedor = cambiar una línea aquí."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.content_agent import ContentAgent
from app.agents.graph import Agents
from app.agents.media_agent import MediaAgent
from app.agents.storage_agent import StorageAgent
from app.agents.trend_agent import TrendAgent
from app.core.interfaces import (
    ImageProvider, LLMClient, ObjectStorage, Providers, TrendSource, TTSProvider, VideoProvider,
)
from app.core.settings import Settings, get_settings
from app.providers.image_pollinations import PollinationsProvider
from app.providers.llm_openrouter import OpenRouterClient
from app.providers.motion_parallax import ParallaxMotion
from app.providers.storage_r2 import R2Storage
from app.providers.trends.google import GoogleTrendsSource
from app.providers.trends.reddit import RedditSource
from app.providers.trends.wikipedia import WikipediaSource
from app.providers.tts_kokoro import KokoroTTS
from app.providers.video_ffmpeg import FFmpegVideo


def _require(**values: str) -> None:
    missing = [name.upper() for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}")


def build_agents(providers: Providers, session_factory: async_sessionmaker[AsyncSession], settings: Settings | None = None) -> Agents:
    s = settings or get_settings()
    return Agents(
        trend=TrendAgent(providers.trends),
        content=ContentAgent(providers.llm),
        media=MediaAgent(
            providers.tts, providers.images, providers.video, voice=s.tts_voice, lang=s.tts_lang, motion=providers.motion,
        ),
        storage=StorageAgent(session_factory, providers.storage),
    )


def build_providers(settings: Settings | None = None) -> Providers:
    s = settings or get_settings()
    _require(
        openrouter_api_key=s.openrouter_api_key, r2_account_id=s.r2_account_id,
        r2_access_key_id=s.r2_access_key_id, r2_secret_access_key=s.r2_secret_access_key,
    )
    providers = Providers(
        llm=OpenRouterClient(s.openrouter_api_key, s.openrouter_model_list),
        images=PollinationsProvider(s.pollinations_token),
        tts=KokoroTTS(),
        video=FFmpegVideo(),
        storage=R2Storage(s.r2_account_id, s.r2_access_key_id, s.r2_secret_access_key, s.r2_bucket),
        trends=[GoogleTrendsSource(), RedditSource(), WikipediaSource()],
        motion=ParallaxMotion(),
    )
    # Falla al arrancar, no a mitad del pipeline, si una implementación deja de cumplir su contrato.
    checks = [
        (providers.llm, LLMClient), (providers.images, ImageProvider), (providers.tts, TTSProvider),
        (providers.video, VideoProvider), (providers.storage, ObjectStorage),
        *((source, TrendSource) for source in providers.trends),
    ]
    for impl, contract in checks:
        if not isinstance(impl, contract):
            raise TypeError(f"{type(impl).__name__} no cumple {contract.__name__}")
    return providers
