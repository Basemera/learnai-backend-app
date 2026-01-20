from pathlib import Path

import pytest

from app.services.books_service import BookService


def test_upload_book_persists_metadata(tmp_path: Path) -> None:
    metadata_path = tmp_path / "data" / "books.json"
    uploads_dir = tmp_path / "uploads"
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4 fake content")

    service = BookService(metadata_path=metadata_path, uploads_dir=uploads_dir)
    service._extract_pdf_text = (  # type: ignore[assignment]
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
    assert metadata_path.exists()
    assert any(uploads_dir.iterdir())


def test_list_and_get_books(tmp_path: Path) -> None:
    metadata_path = tmp_path / "data" / "books.json"
    uploads_dir = tmp_path / "uploads"
    source = tmp_path / "sample.epub"
    source.write_bytes(b"fake epub")

    service = BookService(metadata_path=metadata_path, uploads_dir=uploads_dir)
    service._extract_epub_text = (  # type: ignore[assignment]
        lambda path, preserve_format=False: ("word " * 50, None)
    )

    details = service.upload_book(file_path=str(source), title="Epub Book")
    items = service.list_books()
    fetched = service.get_book(details.id)

    assert len(items) == 1
    assert items[0].id == details.id
    assert fetched.title == "Epub Book"


def test_upload_book_rejects_unsupported_format(tmp_path: Path) -> None:
    metadata_path = tmp_path / "data" / "books.json"
    uploads_dir = tmp_path / "uploads"
    source = tmp_path / "sample.txt"
    source.write_text("plain")

    service = BookService(metadata_path=metadata_path, uploads_dir=uploads_dir)

    with pytest.raises(ValueError):
        service.upload_book(file_path=str(source), title="Nope")


def test_read_book_returns_text_counts(tmp_path: Path) -> None:
    metadata_path = tmp_path / "data" / "books.json"
    uploads_dir = tmp_path / "uploads"
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4 fake content")

    service = BookService(metadata_path=metadata_path, uploads_dir=uploads_dir)
    service._extract_pdf_text = (  # type: ignore[assignment]
        lambda path, preserve_format=False: ("one two three four", 2)
    )

    details = service.upload_book(file_path=str(source), title="Count Book")
    text, word_count, total_chunks = service.read_book(details.id)

    assert text == "one two three four"
    assert word_count == 4
    assert total_chunks == 1
