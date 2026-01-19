import pytest
from pydantic import ValidationError

from app.schemas.books import BookDetails, BookListItem


def test_book_list_item_accepts_valid_payload() -> None:
    item = BookListItem(
        id="book_1",
        title="Deep Learning 101",
        author="A. Writer",
        format="pdf",
        progress_percent=42.5,
    )

    assert item.id == "book_1"
    assert item.title == "Deep Learning 101"
    assert item.progress_percent == 42.5


def test_book_list_item_rejects_empty_title() -> None:
    with pytest.raises(ValidationError):
        BookListItem(id="book_1", title="")


def test_book_list_item_rejects_progress_out_of_range() -> None:
    with pytest.raises(ValidationError):
        BookListItem(id="book_1", title="Valid", progress_percent=120)


def test_book_details_accepts_valid_payload() -> None:
    details = BookDetails(
        id="book_1",
        title="Neural Networks",
        author="A. Writer",
        language="en",
        format="epub",
        page_count=200,
        word_count=45000,
        total_chunks=12,
    )

    assert details.page_count == 200
    assert details.total_chunks == 12


def test_book_details_rejects_short_language_code() -> None:
    with pytest.raises(ValidationError):
        BookDetails(id="book_1", title="Valid", language="e")
