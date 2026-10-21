from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_ignore_empty: una variable vacía (p. ej. un secret opcional de Actions) no pisa el valor por defecto
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore", env_ignore_empty=True)

    database_url: str
    cors_origins: str = "http://localhost:3000"
    api_key: str = ""
    assets_base_url: str = ""  # p. ej. https://contentos-worker.<cuenta>.workers.dev/artifacts
    artifact_secret: str = ""  # el mismo que el Worker: firma las URLs de descarga
    artifact_url_ttl: int = 3600
    default_user_email: str = "admin@local"
    log_level: str = "INFO"

    # Pipeline (providers). El portal solo muestra modelos y voz.
    openrouter_api_key: str = ""
    # Los modelos gratuitos cambian a diario: orden según la prueba de scripts/check_models.py (workflow models-check)
    openrouter_models: str = (
        "minimax/minimax-m3.1-flash:free,nvidia/nemotron-3-ultra-550b-a55b:free,openrouter/free,poolside/laguna-s-2.1:free,"
        "nvidia/nemotron-3.5-lightning:free,google/gemma-4-31b-it:free,google/gemma-4-26b-a4b-it:free,"
        "dots-studio/dots-3-note-preview:free"
    )
    pollinations_token: str = ""  # opcional: el acceso anónimo funciona
    tts_voice: str = "ef_dora"
    tts_lang: str = "e"
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "contentos"

    # Límites del free tier usados por UsageService
    openrouter_daily_limit: int = 50
    r2_limit_mb: int = 10_240
    db_limit_mb: int = 500
    warn_ratio: float = 0.8

    @property
    def openrouter_model_list(self) -> list[str]:
        return [m.strip() for m in self.openrouter_models.split(",") if m.strip()]

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
