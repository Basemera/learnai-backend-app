"""Alembic environment configuration.

Uses SQLAlchemy 2.0 style and reads DATABASE_URL from the environment so that
the same migrations work in local dev, CI, and managed Postgres deployments.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Alembic config object – gives access to .ini values
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import all models so that Base.metadata is fully populated
# ---------------------------------------------------------------------------
import app.models.book  # noqa: E402, F401
import app.models.embedding  # noqa: E402, F401
from app.models.base import Base  # noqa: E402

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# URL helper – always prefer DATABASE_URL env var over alembic.ini value
# ---------------------------------------------------------------------------
def _get_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Export it before running Alembic migrations."
        )
    return url


# ---------------------------------------------------------------------------
# Offline migrations (generates SQL without connecting to the DB)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (connects to the DB and runs migrations)
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
