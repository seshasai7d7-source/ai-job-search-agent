from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import ROOT_DIR, settings


def _database_url():
    url = make_url(settings.database_url)
    if url.get_backend_name() != "sqlite" or url.database in (None, "", ":memory:"):
        return url

    database_path = Path(url.database)
    if not database_path.is_absolute():
        database_path = ROOT_DIR / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return url.set(database=str(database_path))


DATABASE_URL = _database_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.get_backend_name() == "sqlite" else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
