from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.models.book import Book
from app.services.books_service import BookService


class FakeBooksRepository:
    """In-memory repository for unit-testing BookService without a real DB."""

    def __init__(self) -> None:
        self._books: dict[str, Book] = {}

    def list_books(self) -> list[Book]:
        return list(self._books.values())

    def get_book(self, book_id: str) -> Book | None:
        return self._books.get(book_id)

    def create_book(self, book: Book) -> Book:
        self._books[book.id] = book
        return book


def _make_service(tmp_path: Path) -> BookService:
    uploads_dir = tmp_path / "uploads"
    repo: Any = FakeBooksRepository()
    return BookService(repo=repo, uploads_dir=uploads_dir)


def test_upload_book_persists_record(tmp_path: Path) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4 fake content")

    service = _make_service(tmp_path)
    service._extract_pdf_text = (  # type: ignore[method-assign]
        lambda path, preserve_format=False: ("hello world", 3)
    )

    details = service.upload_book(
        file_path=str(source),
        title="Sample Book",
        author="A. Writer",
        language="en",
    )

    assert details.title == "Sample Book"
    assert details.page_count == 3
    assert details.id
    # File should be copied into uploads_dir
    uploads_dir = tmp_path / "uploads"
    assert any(uploads_dir.iterdir())


def test_list_and_get_books(tmp_path: Path) -> None:
    source = tmp_path / "sample.epub"
    source.write_bytes(b"fake epub")

    service = _make_service(tmp_path)
    service._extract_epub_text = (  # type: ignore[method-assign]
        lambda path, preserve_format=False: ("word " * 50, None)
    )

    details = service.upload_book(file_path=str(source), title="Epub Book")
    items = service.list_books()
    fetched = service.get_book(details.id)

    assert len(items) == 1
    assert items[0].id == details.id
    assert fetched.title == "Epub Book"


def test_upload_book_rejects_unsupported_format(tmp_path: Path) -> None:
    source = tmp_path / "sample.txt"
    source.write_text("plain")

    service = _make_service(tmp_path)

    with pytest.raises(ValueError):
        service.upload_book(file_path=str(source), title="Nope")


def test_read_book_returns_text_counts(tmp_path: Path) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4 fake content")

    service = _make_service(tmp_path)
    service._extract_pdf_text = (  # type: ignore[method-assign]
        lambda path, preserve_format=False: ("one two three four", 2)
    )

    details = service.upload_book(file_path=str(source), title="Count Book")
    text, word_count, total_chunks = service.read_book(details.id)

    assert text == "one two three four"
    assert word_count == 4
    assert total_chunks == 1
