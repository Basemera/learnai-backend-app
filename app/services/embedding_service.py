"""Embeddings service: chunks book text and stores vectors in Postgres via pgvector."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.models.embedding import TEXT_EMBEDDING_3_SMALL_DIMS
from app.repositories.books_repository import BooksRepository
from app.repositories.embeddings_repository import EmbeddingsRepository
from app.services import text_extraction
from app.services.openai_service import get_openai_service

# OpenAI provider identifier stored in the embedding_models table
_OPENAI_PROVIDER = "openai"


class EmbeddingsService:
    def __init__(
        self,
        books_repo: BooksRepository,
        embeddings_repo: EmbeddingsRepository,
        embedding_model: str = "text-embedding-3-small",
        chunk_size_words: int = 400,
        overlap_words: int = 50,
        batch_size: int = 64,
    ) -> None:
        self.books_repo = books_repo
        self.embeddings_repo = embeddings_repo
        self.embedding_model = embedding_model
        self.chunk_size_words = chunk_size_words
        self.overlap_words = overlap_words
        self.batch_size = batch_size

    def index_book(self, book_id: str) -> None:
        """Background-task entrypoint.  Persists job status and chunks in Postgres."""
        record = self.books_repo.get_book(book_id)
        file_path = record.file_path if record else None

        em = self.embeddings_repo.get_or_create_embedding_model(
            name=self.embedding_model,
            provider=_OPENAI_PROVIDER,
            dimensions=TEXT_EMBEDDING_3_SMALL_DIMS,
        )

        if not file_path:
            self.embeddings_repo.upsert_job_status(
                book_id=book_id,
                model_id=em.id,
                status="failed",
                chunk_size_words=self.chunk_size_words,
                overlap_words=self.overlap_words,
                error="Book file path is missing.",
            )
            return

        self.embeddings_repo.upsert_job_status(
            book_id=book_id,
            model_id=em.id,
            status="pending",
            chunk_size_words=self.chunk_size_words,
            overlap_words=self.overlap_words,
        )

        try:
            text = self._extract_book_text(
                Path(file_path),
                file_format=record.format,  # type: ignore[union-attr]
                preserve_format=True,
            )
            chunks = self._chunk_text_words(text)
            embeddings = self._embed_chunks([c["text"] for c in chunks])

            chunk_records: list[dict[str, Any]] = [
                {
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "embedding": embeddings[i],
                }
                for i, chunk in enumerate(chunks)
            ]

            self.embeddings_repo.replace_chunks(book_id, em.id, chunk_records)
            self.embeddings_repo.upsert_job_status(
                book_id=book_id,
                model_id=em.id,
                status="ready",
                chunk_size_words=self.chunk_size_words,
                overlap_words=self.overlap_words,
            )
        except Exception as exc:
            self.embeddings_repo.upsert_job_status(
                book_id=book_id,
                model_id=em.id,
                status="failed",
                chunk_size_words=self.chunk_size_words,
                overlap_words=self.overlap_words,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _extract_book_text(
        self, path: Path, *, file_format: str | None, preserve_format: bool
    ) -> str:
        fmt = file_format or text_extraction.detect_format(path)
        extracted_text, _ = text_extraction.extract_text(path, fmt, preserve_format=preserve_format)
        return extracted_text

    def _chunk_text_words(self, text: str) -> list[dict[str, Any]]:
        if not text:
            return []
        words = text.split()
        chunks: list[dict[str, Any]] = []
        idx = 0
        chunk_index = 0
        while idx < len(words):
            end = min(idx + self.chunk_size_words, len(words))
            chunk_words = words[idx:end]
            chunk_text = " ".join(chunk_words).strip()
            if chunk_text:
                chunks.append({"chunk_index": chunk_index, "text": chunk_text})
                chunk_index += 1
            idx = end
            if idx < len(words):
                idx = max(0, idx - self.overlap_words)
        return chunks

    def _embed_chunks(self, chunk_texts: list[str]) -> list[list[float]]:
        if not chunk_texts:
            return []
        service = get_openai_service()
        vectors: list[list[float]] = []
        for start in range(0, len(chunk_texts), self.batch_size):
            batch = chunk_texts[start : start + self.batch_size]
            vectors.extend(service.embed_texts(batch, model=self.embedding_model))
        return vectors
