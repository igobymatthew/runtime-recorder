from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

DEFAULT_DB_URL = "sqlite:///afr.db"


def database_url() -> str:
    return os.getenv("AFR_DB_URL", DEFAULT_DB_URL)


def make_engine(db_url: str | None = None) -> Engine:
    url = db_url or database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine()


def init_db(db_engine: Engine | None = None) -> None:
    SQLModel.metadata.create_all(db_engine or engine)


def get_session() -> Generator[Session, None, None]:
    init_db(engine)
    with Session(engine) as session:
        yield session
