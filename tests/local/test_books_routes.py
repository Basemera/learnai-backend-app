from pathlib import Path
from typing import Optional

from fastapi.testclient import TestClient

from app.main import app
from app.routes import books as books_routes
from app.schemas.books import BookDetails, BookListItem


class DummyBooksService:
    def __init__(self) -> None:
        self.last_file_path: Optional[str] = None

    def list_books(self) -> list[BookListItem]:
        return [
            BookListItem(
                id="book_1",
                title="Test Book",
                author="A. Writer",
                format="pdf",
                progress_percent=25.0,
            )
        ]

    def get_book(self, book_id: str) -> BookDetails:
        return BookDetails(
            id=book_id,
            title="Test Book",
            author="A. Writer",
            description=None,
            language=None,
            format="pdf",
            page_count=10,
            word_count=1000,
            total_chunks=3,
            created_at=None,
        )

    def read_book(self, book_id: str) -> tuple[str, int, int]:
        return ("hello", 1, 1)

    def upload_book(
        self,
        file_path: str,
        title: str,
        author: Optional[str] = None,
        language: Optional[str] = None,
        description: Optional[str] = None,
    ) -> BookDetails:
        self.last_file_path = file_path
        assert Path(file_path).exists()
        return BookDetails(
            id="book_2",
            title=title,
            author=author,
            description=description,
            language=language,
            format="pdf",
            page_count=None,
            word_count=None,
            total_chunks=None,
            created_at=None,
        )


class DummyEmbeddingService:
    def index_book(self, book_id: str) -> None:
        self.book_id = book_id


def test_get_books_list() -> None:
    dummy = DummyBooksService()
    app.dependency_overrides[books_routes.get_book_service] = lambda: dummy
    client = TestClient(app)

    response = client.get("/books/")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == "book_1"
    assert payload[0]["title"] == "Test Book"
    app.dependency_overrides.clear()


def test_get_book_details() -> None:
    dummy = DummyBooksService()
    app.dependency_overrides[books_routes.get_book_service] = lambda: dummy
    client = TestClient(app)

    response = client.get("/books/book_1")

    assert response.status_code == 200
    assert response.json()["id"] == "book_1"
    app.dependency_overrides.clear()


def test_read_book() -> None:
    dummy = DummyBooksService()
    app.dependency_overrides[books_routes.get_book_service] = lambda: dummy
    client = TestClient(app)

    response = client.post("/books/book_1/read")

    assert response.status_code == 200
    assert response.json() == {
        "id": "book_1",
        "text": "hello",
        "word_count": 1,
        "total_chunks": 1,
    }
    app.dependency_overrides.clear()


def test_upload_book() -> None:
    dummy = DummyBooksService()
    embedding_dummy = DummyEmbeddingService()
    app.dependency_overrides[books_routes.get_book_service] = lambda: dummy
    app.dependency_overrides[books_routes.get_embedding_service] = lambda: embedding_dummy
    client = TestClient(app)

    response = client.post(
        "/books/upload",
        files={"file": ("sample.pdf", b"%PDF-1.4", "application/pdf")},
        data={"title": "Upload Book", "author": "Uploader"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Upload Book"
    assert dummy.last_file_path is not None
    assert not Path(dummy.last_file_path).exists()
    app.dependency_overrides.clear()
