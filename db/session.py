from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from paths import get_portable_dir


DATABASE_NAME = "orzalan.db"


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    data_dir = get_portable_dir("data")
    db_path = data_dir / DATABASE_NAME
    return create_engine(f"sqlite:///{db_path}", future=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_session() -> Session:
    return SessionLocal()
