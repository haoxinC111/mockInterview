from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.models import db as db_models  # noqa: F401


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    # Ensure model metadata is imported before table creation.
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
