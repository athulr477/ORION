"""Alembic migration environment for Orion.

Configures synchronous migrations with proper pgvector type registration.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the project root is on sys.path so we can import orion
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pgvector.sqlalchemy import Vector  # noqa: E402

from orion.config import settings  # noqa: E402
from orion.database import Base  # noqa: E402

# Import all models so that Base.metadata is fully populated
import orion.models  # noqa: E402, F401

# Alembic Config object
config = context.config

# Override sqlalchemy.url with the sync URL from our settings
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to the database)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Register pgvector type so Alembic recognizes it
        connection.dialect.ischema_names["vector"] = Vector

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
