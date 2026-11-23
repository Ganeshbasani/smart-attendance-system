"""Alembic migration environment, wired to the app's settings and metadata."""

import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401  register models on Base.metadata

config = context.config
if config.config_file_name is not None and not logging.getLogger().handlers:
    # Apply alembic.ini logging only for standalone CLI runs (alembic upgrade
    # ...), where nothing has configured logging yet. When the app runs
    # migrations at startup it has already called configure_logging(); calling
    # fileConfig anyway would reconfigure the ROOT logger to alembic.ini's
    # [logger_root] level=WARN, silently dropping every application INFO line
    # (request logs, "Liveness metrics", audit trail) for the rest of the
    # process. disable_existing_loggers=False additionally protects named
    # loggers in the CLI case.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Inject the database URL from application settings.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
