from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def ensure_users_birth_place_columns(conn: AsyncConnection) -> None:
    """Upgrade path: existing DBs may lack ORM-mapped columns → 500 on any User load."""
    settings = get_settings()
    schema = settings.db_name
    columns: list[tuple[str, str]] = [
        ("birth_place_name", "VARCHAR(80) NULL"),
        ("birth_place_lat", "DOUBLE NULL"),
        ("birth_place_lon", "DOUBLE NULL"),
        ("birth_tz", "VARCHAR(64) NULL"),
        ("ai_profile", "JSON NULL"),
    ]
    for col_name, col_def in columns:
        r = await conn.execute(
            text(
                """
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = :schema
                  AND TABLE_NAME = 'users'
                  AND COLUMN_NAME = :cname
                """
            ),
            {"schema": schema, "cname": col_name},
        )
        if (r.scalar_one() or 0) == 0:
            await conn.execute(
                text(f"ALTER TABLE users ADD COLUMN `{col_name}` {col_def}")
            )


async def ensure_orders_product_type_enum(conn: AsyncConnection) -> None:
    """Keep MySQL ENUM in sync with Python ProductType — avoids 'Data truncated' on INSERT."""
    import logging
    from app.models.order import ProductType

    logger = logging.getLogger(__name__)
    expected = {e.value for e in ProductType}
    s = get_settings()

    r = await conn.execute(
        text(
            """
            SELECT COLUMN_TYPE FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = :schema
              AND TABLE_NAME = 'orders'
              AND COLUMN_NAME = 'product_type'
            """
        ),
        {"schema": s.db_name},
    )
    row = r.scalar_one_or_none()
    if not row:
        return

    import re
    current = set(re.findall(r"'([^']+)'", row))
    missing = expected - current
    if not missing:
        return

    logger.warning("orders.product_type ENUM missing %s — running ALTER TABLE", missing)
    enum_values = ",".join(f"'{v}'" for v in sorted(expected))
    await conn.execute(
        text(f"ALTER TABLE orders MODIFY COLUMN product_type ENUM({enum_values}) NOT NULL")
    )


async def init_db() -> None:
    from app.models import Base  # noqa: F401 — register models
    from app.models import Article, DailyFortune, DailyGuide, DailyTip, Order, Report, User  # noqa: F401
    from app.models import growth  # noqa: F401 — growth tables

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await ensure_users_birth_place_columns(conn)
        await ensure_orders_product_type_enum(conn)
