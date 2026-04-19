import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Optional

from app.models.book import Book
from app.repositories.books_repository import BooksRepository
from app.schemas.books import BookDetails, BookListItem


class BookService:
    def __init__(
        self,
        repo: BooksRepository,
        uploads_dir: Optional[Path] = None,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        self.repo = repo
        self.uploads_dir = uploads_dir or root / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def list_books(self) -> list[BookListItem]:
        rows = self.repo.list_books()
        return [
            BookListItem(
                id=row.id,
                title=row.title,
                author=row.author,
                format=row.format,
                progress_percent=None,
            )
            for row in rows
        ]

    def get_book(self, book_id: str) -> BookDetails:
        row = self.repo.get_book(book_id)
        if row is None:
            raise ValueError(f"Book {book_id} not found.")
        return BookDetails(
            id=row.id,
            title=row.title,
            author=row.author,
            description=row.description,
            language=row.language,
            format=row.format,
            page_count=row.page_count,
            word_count=row.word_count,
            total_chunks=row.total_chunks,
            created_at=row.created_at,
        )

    def read_book(self, book_id: str) -> tuple[str, int, int]:
        row = self.repo.get_book(book_id)
        if row is None:
            raise ValueError(f"Book {book_id} not found.")
        text, _page_count = self._extract_text(
            Path(row.file_path),
            row.format,
            preserve_format=True,
        )
        word_count = self._count_words(text)
        total_chunks = self._count_chunks(text)
        return text, word_count, total_chunks

    def upload_book(
        self,
        file_path: str,
        title: str,
        author: Optional[str] = None,
        language: Optional[str] = None,
        description: Optional[str] = None,
    ) -> BookDetails:
        source_path = Path(file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_format = self._detect_format(source_path)
        book_id = __import__("uuid").uuid4().hex
        destination = self.uploads_dir / f"{book_id}{source_path.suffix.lower()}"
        __import__("shutil").copyfile(source_path, destination)

        text, page_count = self._extract_text(destination, file_format, preserve_format=False)
        word_count = self._count_words(text)
        total_chunks = self._count_chunks(text)

        row = Book(
            id=book_id,
            title=title,
            author=author,
            description=description,
            language=language,
            format=file_format,
            page_count=page_count,
            word_count=word_count,
            total_chunks=total_chunks,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            file_path=str(destination),
        )
        row = self.repo.create_book(row)
        return self.get_book(row.id)

    def _detect_format(self, source_path: Path) -> str:
        suffix = source_path.suffix.lower()
        if suffix == ".pdf":
            return "pdf"
        if suffix == ".epub":
            return "epub"
        raise ValueError("Only PDF and EPUB formats are supported.")

    def _extract_text(
        self,
        path: Path,
        file_format: str,
        preserve_format: bool = False,
    ) -> tuple[str, Optional[int]]:
        if file_format == "pdf":
            return self._extract_pdf_text(path, preserve_format=preserve_format)
        if file_format == "epub":
            return self._extract_epub_text(path, preserve_format=preserve_format)
        raise ValueError("Unsupported format.")

    def _extract_pdf_text(
        self,
        path: Path,
        preserve_format: bool = False,
    ) -> tuple[str, Optional[int]]:
        try:
            import pdfplumber
        except ImportError as exc:
            raise ValueError("pdfplumber is required to extract PDF text.") from exc

        texts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                if preserve_format:
                    try:
                        page_text = (
                            page.extract_text(
                                layout=True,
                                x_tolerance=2,
                                y_tolerance=2,
                            )
                            or ""
                        )
                    except TypeError:
                        page_text = page.extract_text() or ""
                    if self._looks_unspaced(page_text):
                        page_text = self._extract_pdf_words(page)
                    page_text = self._normalize_bullets(page_text)
                    texts.append(f"--- Page {page_number} ---\n{page_text}".rstrip())
                else:
                    texts.append(page.extract_text() or "")
            page_count = len(pdf.pages)
        return "\n".join(texts).strip(), page_count

    def _extract_epub_text(
        self,
        path: Path,
        preserve_format: bool = False,
    ) -> tuple[str, Optional[int]]:
        try:
            from ebooklib import ITEM_DOCUMENT, epub
        except ImportError as exc:
            raise ValueError("ebooklib is required to extract EPUB text.") from exc

        book = epub.read_epub(str(path))
        texts: list[str] = []
        for item in book.get_items_of_type(ITEM_DOCUMENT):
            content = item.get_content().decode("utf-8", errors="ignore")
            if preserve_format:
                texts.append(content)
            else:
                texts.append(self._strip_html(content))
        return "\n".join(texts).strip(), None

    def _strip_html(self, content: str) -> str:
        text = re.sub(r"<[^>]+>", " ", content)
        text = unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def _looks_unspaced(self, text: str, min_length: int = 200) -> bool:
        if not text or len(text) < min_length:
            return False
        space_ratio = text.count(" ") / max(len(text), 1)
        return space_ratio < 0.01

    def _extract_pdf_words(self, page: Any) -> str:
        words = page.extract_words(use_text_flow=True)
        if not words:
            return ""
        lines: list[list[dict]] = []
        for word in words:
            if not lines:
                lines.append([word])
                continue
            last_line = lines[-1]
            if abs(word["top"] - last_line[-1]["top"]) <= 3:
                last_line.append(word)
            else:
                lines.append([word])
        rendered_lines = [" ".join(item["text"] for item in line) for line in lines]
        return "\n".join(rendered_lines)

    def _normalize_bullets(self, text: str) -> str:
        if not text:
            return text
        text = re.sub(r"(?<!^)(?<!\n)(?=[•●○])", "\n", text)
        text = re.sub(r"(?<!^)(?<!\n)[ \t]*([•●○])", r"\n\1", text)
        text = re.sub(r"([•●○])(?!\s)", r"\1 ", text)
        text = re.sub(r"(?<!^)(\s+-\s+)", r"\n\1", text)
        return text

    def _count_words(self, text: str) -> int:
        if not text:
            return 0
        return len(text.split())

    def _count_chunks(self, text: str, chunk_size: int = 400, overlap: int = 50) -> int:
        if not text:
            return 0
        words = text.split()
        total = 0
        index = 0
        while index < len(words):
            total += 1
            index += chunk_size
            if index < len(words):
                index -= overlap
        return total


_service: Optional[BookService] = None


def get_books_service() -> BookService:
    global _service
    if _service is None:
        _service = BookService()
    return _service
