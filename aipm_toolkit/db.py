from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine():
    settings = get_settings()
    url = settings.database_url
    if settings.mode == "desktop":
        url = URL.create("sqlite", database=str(settings.data_dir / "workspace.sqlite3"))
    kwargs = {"pool_pre_ping": True}
    if str(url).startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if settings.mode == "desktop":
            kwargs["connect_args"]["timeout"] = 30
    engine = create_engine(url, **kwargs)
    if settings.mode == "desktop":
        @event.listens_for(engine, "connect")
        def configure_sqlite(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=30000")
    return engine


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
