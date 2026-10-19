from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.errors import register_handlers
from app.core.logging import log_requests, setup_logging
from app.core.settings import get_settings

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(title="Content OS API")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_methods=["*"], allow_headers=["*"])
app.middleware("http")(log_requests)
register_handlers(app)
app.include_router(api_router)
