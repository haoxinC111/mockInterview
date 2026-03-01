from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.models import db as db_models  # noqa: F401


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    # Ensure model metadata is imported before table creation.
    SQLModel.metadata.create_all(engine)
    # Lightweight migration: add columns that may not exist in older databases.
    _migrate_add_column("interviewsession", "city", "TEXT DEFAULT '北京'")
    _migrate_add_column("interviewsession", "answer_style", "TEXT DEFAULT 'concise'")


def get_session():
    with Session(engine) as session:
        yield session


def _migrate_add_column(table: str, column: str, col_type: str) -> None:
    """Add a column to *table* if it does not already exist (SQLite only)."""
    import sqlalchemy

    with engine.connect() as conn:
        try:
            conn.execute(sqlalchemy.text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            conn.commit()
        except Exception:
            # Column already exists — safe to ignore.
            pass
