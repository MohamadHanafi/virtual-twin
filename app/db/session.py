import os
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.constants.database import DATABASE_URL_ENV, DEFAULT_DATABASE_URL
from app.constants.paths import PROJECT_ROOT
from app.db.base import Base
import app.db.models  # noqa: F401

load_dotenv(PROJECT_ROOT / ".env")


def get_database_url() -> str:
    database_url = os.getenv(DATABASE_URL_ENV, DEFAULT_DATABASE_URL)

    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return database_url


@lru_cache(maxsize=1)
def get_engine():
    database_url = get_database_url()
    if database_url == DEFAULT_DATABASE_URL:
        (PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


def init_db():
    Base.metadata.create_all(bind=get_engine())


def get_db():
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
