from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ContentStatus, Platform


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]+$", max_length=60)
    name: str = Field(min_length=1, max_length=120)
    niche: str = ""
    language: str = "es"
    config: dict[str, Any] = {}


class ProjectOut(ORMModel):
    id: UUID
    slug: str
    name: str
    niche: str
    language: str
    config: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TopicCreate(BaseModel):
    project_id: UUID
    topic: str = Field(min_length=1, max_length=300)
    keywords: list[str] = []
    source: str = "manual"
    score: float = Field(default=0, ge=0)


class TopicOut(ORMModel):
    id: UUID
    project_id: UUID
    topic: str
    keywords: list[str]
    source: str
    score: float
    created_at: datetime


class ContentCreate(BaseModel):
    project_id: UUID
    topic_id: UUID | None = None
    title: str = ""


class StatusUpdate(BaseModel):
    status: ContentStatus


class ContentOut(ORMModel):
    id: UUID
    project_id: UUID
    topic_id: UUID | None
    status: ContentStatus
    title: str
    hook: str
    script: str
    caption: str
    hashtags: list[str]
    cta: str
    duration_seconds: float
    llm_provider: str
    model_name: str
    tokens_used: int
    last_error: str
    created_at: datetime
    updated_at: datetime


class ContentSummary(ORMModel):
    """Fila liviana para listas: sin hook, guion, caption, hashtags ni cta."""

    id: UUID
    project_id: UUID
    topic_id: UUID | None
    status: ContentStatus
    title: str
    llm_provider: str
    model_name: str
    tokens_used: int
    last_error: str
    duration_seconds: float
    created_at: datetime
    updated_at: datetime


class AssetOut(ORMModel):
    id: UUID
    content_id: UUID
    kind: str
    storage_provider: str
    storage_key: str
    file_size: int
    mime_type: str
    url: str | None = None
    created_at: datetime


class PublishIn(BaseModel):
    platform: Platform
    published_at: datetime | None = None
    notes: str = ""


class PublicationCreate(PublishIn):
    content_id: UUID


class PublicationOut(ORMModel):
    id: UUID
    content_id: UUID
    platform: Platform
    published_at: datetime
    notes: str
    created_at: datetime


class DashboardStats(BaseModel):
    total: int
    approved: int
    published: int
    rejected: int
    pending: int
    topics: int
    queued: int  # esperan al pipeline (idea/guion sin error)
    failed: int  # idea/guion con error: esperan un reintento manual


class QueueStatus(BaseModel):
    pending: int
    failed: int


class SystemLimits(BaseModel):
    estimated_tokens_used: int
    estimated_storage_mb: float
    estimated_content_count: int
    free_tier_warnings: list[str]
    storage_limit_mb: int
    llm_calls_today: int
    llm_daily_limit: int


class SystemConfig(BaseModel):
    llm_provider: str
    llm_models: list[str]
    image_provider: str
    tts_provider: str
    tts_voice: str
    tts_lang: str
    openrouter_daily_limit: int
    r2_limit_mb: int
    db_limit_mb: int
    assets_configured: bool
