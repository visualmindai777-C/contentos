import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# El esquema real vive en db/schema.sql (FKs, CHECKs, triggers). Aquí solo el mapeo.


class Base(DeclarativeBase):
    pass


class Entity(Base):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Entity):
    __tablename__ = "users"

    email: Mapped[str]
    name: Mapped[str] = mapped_column(default="")


class Project(Entity):
    __tablename__ = "projects"

    user_id: Mapped[uuid.UUID]
    slug: Mapped[str]
    name: Mapped[str]
    niche: Mapped[str] = mapped_column(default="")
    language: Mapped[str] = mapped_column(default="es")
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True)


class Topic(Entity):
    __tablename__ = "topics"

    project_id: Mapped[uuid.UUID]
    topic: Mapped[str]
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    source: Mapped[str]
    summary: Mapped[str] = mapped_column(default="")
    score: Mapped[float] = mapped_column(Numeric(6, 2, asdecimal=False), default=0)


class Content(Entity):
    __tablename__ = "contents"

    project_id: Mapped[uuid.UUID]
    topic_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="idea")
    title: Mapped[str] = mapped_column(default="")
    hook: Mapped[str] = mapped_column(default="")
    script: Mapped[str] = mapped_column(default="")
    caption: Mapped[str] = mapped_column(default="")
    hashtags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    cta: Mapped[str] = mapped_column(default="")
    duration_seconds: Mapped[float] = mapped_column(Numeric(6, 2, asdecimal=False), default=0)
    llm_provider: Mapped[str] = mapped_column(default="")
    model_name: Mapped[str] = mapped_column(default="")
    tokens_used: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str] = mapped_column(default="")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    part: Mapped[int] = mapped_column(default=1)


class Asset(Entity):
    __tablename__ = "assets"

    content_id: Mapped[uuid.UUID]
    kind: Mapped[str]
    storage_provider: Mapped[str] = mapped_column(default="r2")
    storage_key: Mapped[str]
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    mime_type: Mapped[str] = mapped_column(default="")


class Publication(Entity):
    __tablename__ = "publications"

    content_id: Mapped[uuid.UUID]
    platform: Mapped[str]
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(default="")
