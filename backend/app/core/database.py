from collections.abc import AsyncIterator
from uuid import uuid4

from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import get_settings

# Compatible con el pooler de Supabase (pgbouncer en modo transacción): sin prepared statements.
_url = make_url(get_settings().database_url).update_query_dict({"prepared_statement_cache_size": "0"})

engine = create_async_engine(
    _url,
    pool_size=3,
    max_overflow=2,
    pool_pre_ping=True,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    },
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
