"""SQLAlchemy models for pgvector-backed embedding storage.

Tables
------
embedding_models
    Registry of supported embedding models (e.g. text-embedding-3-small).

book_embedding_jobs
    Per-book, per-model indexing job with status tracking.

book_embedding_chunks_1536
    Chunk text + vector(1536) embeddings for models with 1536 dimensions
    (text-embedding-3-small, text-embedding-ada-002).
    Separate tables per dimension keep vector(N) type-safe and allow
    independent pgvector ANN indexes for each dimension.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# ---------------------------------------------------------------------------
# Dimension constant for text-embedding-3-small (OpenAI default = 1536)
# ---------------------------------------------------------------------------
TEXT_EMBEDDING_3_SMALL_DIMS = 1536


def _new_id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmbeddingModel(Base):
    """Registry row for a supported embedding model."""

    __tablename__ = "embedding_models"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class BookEmbeddingJob(Base):
    """Indexing job status for a (book, embedding_model) pair."""

    __tablename__ = "book_embedding_jobs"
    __table_args__ = (
        UniqueConstraint("book_id", "embedding_model_id", name="uq_book_embedding_job"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    book_id: Mapped[str] = mapped_column(String, ForeignKey("books.id"), nullable=False)
    embedding_model_id: Mapped[str] = mapped_column(
        String, ForeignKey("embedding_models.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_size_words: Mapped[int] = mapped_column(Integer, nullable=False)
    overlap_words: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class BookEmbeddingChunk1536(Base):
    """Chunk text + 1536-dim embedding vector for a book.

    The table name encodes the dimension so that future models with different
    dimensions can use separate tables with correctly-sized vector columns.
    """

    __tablename__ = "book_embedding_chunks_1536"
    __table_args__ = (
        Index(
            "ix_book_embedding_chunks_1536_book_model_chunk",
            "book_id",
            "embedding_model_id",
            "chunk_index",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    book_id: Mapped[str] = mapped_column(String, ForeignKey("books.id"), nullable=False)
    embedding_model_id: Mapped[str] = mapped_column(
        String, ForeignKey("embedding_models.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # vector(1536) — requires the pgvector Postgres extension.
    embedding: Mapped[list[float]] = mapped_column(
        Vector(TEXT_EMBEDDING_3_SMALL_DIMS), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
