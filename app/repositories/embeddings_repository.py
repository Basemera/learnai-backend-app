"""Repository for pgvector-backed embeddings storage."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.embedding import BookEmbeddingChunk1536, BookEmbeddingJob, EmbeddingModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmbeddingsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Embedding model registry
    # ------------------------------------------------------------------

    def get_or_create_embedding_model(
        self,
        name: str,
        provider: str,
        dimensions: int,
    ) -> EmbeddingModel:
        """Return the EmbeddingModel row for *name*, creating it if absent."""
        stmt = select(EmbeddingModel).where(EmbeddingModel.name == name)
        existing = self.db.scalars(stmt).first()
        if existing is not None:
            return existing

        model = EmbeddingModel(
            name=name,
            provider=provider,
            dimensions=dimensions,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    # ------------------------------------------------------------------
    # Job status
    # ------------------------------------------------------------------

    def upsert_job_status(
        self,
        book_id: str,
        model_id: str,
        status: str,
        chunk_size_words: int,
        overlap_words: int,
        error: str | None = None,
    ) -> BookEmbeddingJob:
        """Insert or update the indexing job for *(book_id, model_id)*."""
        stmt = select(BookEmbeddingJob).where(
            BookEmbeddingJob.book_id == book_id,
            BookEmbeddingJob.embedding_model_id == model_id,
        )
        job = self.db.scalars(stmt).first()
        if job is None:
            job = BookEmbeddingJob(
                book_id=book_id,
                embedding_model_id=model_id,
                status=status,
                error=error,
                chunk_size_words=chunk_size_words,
                overlap_words=overlap_words,
            )
            self.db.add(job)
        else:
            job.status = status
            job.error = error
            job.updated_at = _utcnow()
            job.chunk_size_words = chunk_size_words
            job.overlap_words = overlap_words

        self.db.commit()
        self.db.refresh(job)
        return job

    # ------------------------------------------------------------------
    # Chunk storage
    # ------------------------------------------------------------------

    def replace_chunks(
        self,
        book_id: str,
        model_id: str,
        chunks: list[dict[str, Any]],
    ) -> None:
        """Replace all chunks for *(book_id, model_id)* in a single transaction.

        *chunks* is a list of dicts with keys:
            ``chunk_index`` (int), ``text`` (str), ``embedding`` (list[float]).
        """
        # Delete existing chunks for this book + model
        self.db.execute(
            delete(BookEmbeddingChunk1536).where(
                BookEmbeddingChunk1536.book_id == book_id,
                BookEmbeddingChunk1536.embedding_model_id == model_id,
            )
        )

        # Bulk-insert new chunks
        now = _utcnow()
        rows = [
            BookEmbeddingChunk1536(
                book_id=book_id,
                embedding_model_id=model_id,
                chunk_index=chunk["chunk_index"],
                content=chunk["text"],
                embedding=chunk["embedding"],
                created_at=now,
            )
            for chunk in chunks
        ]
        self.db.add_all(rows)
        self.db.commit()
