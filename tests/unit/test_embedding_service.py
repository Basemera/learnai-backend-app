"""Unit tests for EmbeddingsService with mocked repositories."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from app.repositories.books_repository import BooksRepository
from app.repositories.embeddings_repository import EmbeddingsRepository
from app.services.embedding_service import EmbeddingsService

# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


def _fake_embedding_model(model_id: str = "em-1") -> SimpleNamespace:
    return SimpleNamespace(
        id=model_id,
        name="text-embedding-3-small",
        provider="openai",
        dimensions=1536,
    )


def _fake_job(status: str = "ready") -> SimpleNamespace:
    return SimpleNamespace(id="job-1", status=status)


def _fake_book(
    book_id: str = "book-1",
    file_path: str | None = None,
    fmt: str = "pdf",
) -> SimpleNamespace:
    return SimpleNamespace(id=book_id, format=fmt, file_path=file_path)


def _make_books_repo(book: Any = None) -> Any:
    """Return a MagicMock standing in for BooksRepository."""
    repo = MagicMock(spec=BooksRepository)
    repo.get_book.return_value = book
    return repo


def _make_embeddings_repo() -> Any:
    """Return a MagicMock standing in for EmbeddingsRepository."""
    repo = MagicMock(spec=EmbeddingsRepository)
    repo.get_or_create_embedding_model.return_value = _fake_embedding_model()
    repo.upsert_job_status.return_value = _fake_job()
    return repo


def _make_service(
    book: Any = None,
    embeddings_repo: Any = None,
) -> EmbeddingsService:
    books_repo: Any = _make_books_repo(book)
    emb_repo: Any = embeddings_repo if embeddings_repo is not None else _make_embeddings_repo()
    return EmbeddingsService(
        books_repo=books_repo,
        embeddings_repo=emb_repo,
        embedding_model="text-embedding-3-small",
        chunk_size_words=5,
        overlap_words=1,
    )


# ---------------------------------------------------------------------------
# Tests: missing book / missing file_path
# ---------------------------------------------------------------------------


def test_index_book_not_found_records_failed() -> None:
    """When repo.get_book returns None the job status should be 'failed'."""
    emb_repo = _make_embeddings_repo()
    service = _make_service(book=None, embeddings_repo=emb_repo)

    service.index_book("book-1")

    emb_repo.upsert_job_status.assert_called_once_with(
        book_id="book-1",
        model_id="em-1",
        status="failed",
        chunk_size_words=service.chunk_size_words,
        overlap_words=service.overlap_words,
        error="Book file path is missing.",
    )


def test_index_book_missing_file_path_records_failed() -> None:
    """A Book row with file_path=None should trigger failed status."""
    book = _fake_book(file_path=None)
    emb_repo = _make_embeddings_repo()
    service = _make_service(book=book, embeddings_repo=emb_repo)

    service.index_book("book-1")

    emb_repo.upsert_job_status.assert_called_once_with(
        book_id="book-1",
        model_id="em-1",
        status="failed",
        chunk_size_words=service.chunk_size_words,
        overlap_words=service.overlap_words,
        error="Book file path is missing.",
    )


# ---------------------------------------------------------------------------
# Tests: successful indexing
# ---------------------------------------------------------------------------


def test_index_book_creates_pending_then_ready(tmp_path: Path) -> None:
    """Successful run should set pending, then ready, and call replace_chunks."""
    file_path = str(tmp_path / "book.pdf")
    book = _fake_book(file_path=file_path)
    emb_repo = _make_embeddings_repo()
    service = _make_service(book=book, embeddings_repo=emb_repo)

    def _stub_extract(path: Path, *, file_format: str | None, preserve_format: bool) -> str:
        return "alpha beta gamma delta epsilon"

    def _stub_embed(chunk_texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1536 for _ in chunk_texts]

    service._extract_book_text = _stub_extract  # type: ignore[method-assign]
    service._embed_chunks = _stub_embed  # type: ignore[method-assign]

    service.index_book("book-1")

    # First call: pending
    first_call = emb_repo.upsert_job_status.call_args_list[0]
    assert first_call.kwargs["status"] == "pending"

    # Last call: ready
    last_call = emb_repo.upsert_job_status.call_args_list[-1]
    assert last_call.kwargs["status"] == "ready"

    # Chunks should be stored
    emb_repo.replace_chunks.assert_called_once()
    call_args = emb_repo.replace_chunks.call_args[0]
    assert call_args[0] == "book-1"
    assert call_args[1] == "em-1"
    chunks = call_args[2]
    assert len(chunks) > 0
    assert "chunk_index" in chunks[0]
    assert "text" in chunks[0]
    assert "embedding" in chunks[0]


def test_index_book_replaces_chunks_on_reindex(tmp_path: Path) -> None:
    """Calling index_book a second time must call replace_chunks again."""
    file_path = str(tmp_path / "book.pdf")
    book = _fake_book(file_path=file_path)
    emb_repo = _make_embeddings_repo()
    service = _make_service(book=book, embeddings_repo=emb_repo)

    def _stub_extract(path: Path, *, file_format: str | None, preserve_format: bool) -> str:
        return "one two three four five"

    def _stub_embed(chunk_texts: list[str]) -> list[list[float]]:
        return [[0.2] * 1536 for _ in chunk_texts]

    service._extract_book_text = _stub_extract  # type: ignore[method-assign]
    service._embed_chunks = _stub_embed  # type: ignore[method-assign]

    service.index_book("book-1")
    service.index_book("book-1")

    assert emb_repo.replace_chunks.call_count == 2


# ---------------------------------------------------------------------------
# Tests: failure path
# ---------------------------------------------------------------------------


def test_index_book_extraction_error_records_failed(tmp_path: Path) -> None:
    """An exception during extraction should set status to 'failed' with an error."""
    file_path = str(tmp_path / "book.pdf")
    book = _fake_book(file_path=file_path)
    emb_repo = _make_embeddings_repo()
    service = _make_service(book=book, embeddings_repo=emb_repo)

    def _boom(path: Path, *, file_format: str | None, preserve_format: bool) -> str:
        raise RuntimeError("PDF is corrupted")

    service._extract_book_text = _boom  # type: ignore[method-assign]

    service.index_book("book-1")

    last_call = emb_repo.upsert_job_status.call_args_list[-1]
    assert last_call.kwargs["status"] == "failed"
    assert "PDF is corrupted" in (last_call.kwargs.get("error") or "")


# ---------------------------------------------------------------------------
# Tests: chunking helper
# ---------------------------------------------------------------------------


def test_chunk_text_words_empty() -> None:
    service = _make_service()
    assert service._chunk_text_words("") == []


def test_chunk_text_words_overlap() -> None:
    service = EmbeddingsService(
        books_repo=_make_books_repo(),
        embeddings_repo=_make_embeddings_repo(),
        chunk_size_words=3,
        overlap_words=1,
    )
    # 6 words: [a,b,c], [c,d,e], [e,f]
    chunks = service._chunk_text_words("a b c d e f")
    assert len(chunks) == 3
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["chunk_index"] == 1
    assert chunks[1]["text"].startswith("c")
