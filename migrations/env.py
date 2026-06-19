from logging.config import fileConfig

from sqlalchemy import pool, create_engine

from alembic import context

from app.models import * # noqa: F401
from app.db.session import Base
from app.core.config import settings
import sys
from pathlib import Path


sys.path.append(str(Path(__file__).parent.parent))

config = context.config
fileConfig(config.config_file_name)


target_metadata = Base.metadata


sync_url = str(settings.DATABASE_URL).replace("postgresql+asyncpg://", "postgresql+psycopg2://")

def run_migrations_offline() -> None:
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(sync_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
