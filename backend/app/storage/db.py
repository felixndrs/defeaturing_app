"""Persistence.

The domain objects are stored as JSON documents keyed by id. Analysis results
are deeply nested and read as a whole, so a document store is a better fit than
a relational split, and it keeps the Pydantic model free to evolve. SQLAlchemy
is used rather than raw sqlite3 so the move to Postgres later is a URL change.
"""

from __future__ import annotations

from typing import Iterator, TypeVar

from sqlalchemy import String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from ..config import get_settings
from ..domain.models import AnalysisRun, GeometryModel, Project


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    #: "project" | "model" | "run"
    kind: Mapped[str] = mapped_column(String(32), primary_key=True)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    #: Foreign key used for listing, e.g. a run's project id. Empty when unused.
    parent_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    payload: Mapped[str] = mapped_column(Text)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(settings.database_url, future=True)
        Base.metadata.create_all(_engine)
    return _engine


def session() -> Session:
    return Session(get_engine(), future=True)


T = TypeVar("T", Project, GeometryModel, AnalysisRun)

_KIND = {Project: "project", GeometryModel: "model", AnalysisRun: "run"}


def save(obj: Project | GeometryModel | AnalysisRun, parent_id: str = "") -> None:
    kind = _KIND[type(obj)]
    with session() as s:
        doc = s.get(Document, (kind, obj.id))
        payload = obj.model_dump_json()
        if doc is None:
            s.add(Document(kind=kind, id=obj.id, parent_id=parent_id, payload=payload))
        else:
            doc.payload = payload
            if parent_id:
                doc.parent_id = parent_id
        s.commit()


def load(cls: type[T], obj_id: str) -> T | None:
    with session() as s:
        doc = s.get(Document, (_KIND[cls], obj_id))
        return cls.model_validate_json(doc.payload) if doc else None


def load_all(cls: type[T], parent_id: str | None = None) -> Iterator[T]:
    stmt = select(Document).where(Document.kind == _KIND[cls])
    if parent_id is not None:
        stmt = stmt.where(Document.parent_id == parent_id)
    with session() as s:
        for doc in s.scalars(stmt):
            yield cls.model_validate_json(doc.payload)
