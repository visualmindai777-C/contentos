from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.repositories.metrics import MetricsRepository
from app.schemas.entities import SystemConfig, SystemLimits

DB_MB_PER_CONTENT = 0.007  # ~0,7 MB por cada 100 contenidos (texto + assets + índices)


class UsageService:
    def __init__(self, session: AsyncSession):
        self.metrics = MetricsRepository(session)
        self.settings = get_settings()

    async def limits(self) -> SystemLimits:
        s = self.settings
        day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        m = await self.metrics.snapshot(day_start)
        content_count, tokens, storage_mb = m.total, m.tokens, round(m.asset_bytes / 1_048_576, 2)
        calls_today = m.llm_calls  # cota superior: cualquier edición cuenta

        checks = [
            ("R2", storage_mb, s.r2_limit_mb, "MB", "borra rechazados o migra a R2 de pago"),
            ("Supabase", content_count * DB_MB_PER_CONTENT, s.db_limit_mb, "MB (estimado)", "migra a Postgres propio"),
            ("OpenRouter", calls_today, s.openrouter_daily_limit, "llamadas hoy (estimado)", "reduce regeneraciones o carga créditos"),
        ]
        warnings = [
            f"{name} al {used / limit:.0%}: {used:g}/{limit} {unit}. Acción: {action}."
            for name, used, limit, unit, action in checks
            if used >= limit * s.warn_ratio
        ]
        return SystemLimits(
            estimated_tokens_used=tokens,
            estimated_storage_mb=storage_mb,
            estimated_content_count=content_count,
            free_tier_warnings=warnings,
            storage_limit_mb=s.r2_limit_mb,
            llm_calls_today=calls_today,
            llm_daily_limit=s.openrouter_daily_limit,
        )

    def config(self) -> SystemConfig:
        s = self.settings
        return SystemConfig(
            llm_provider="openrouter",
            llm_models=[m.strip() for m in s.openrouter_models.split(",") if m.strip()],
            image_provider="pollinations",
            tts_provider="kokoro",
            tts_voice=s.tts_voice,
            tts_lang=s.tts_lang,
            openrouter_daily_limit=s.openrouter_daily_limit,
            r2_limit_mb=s.r2_limit_mb,
            db_limit_mb=s.db_limit_mb,
            assets_configured=bool(s.assets_base_url),
        )
