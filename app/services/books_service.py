import json
import re
import shutil
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.schemas.books import BookDetails, BookListItem


class BookService:
    def __init__(
        self,
        metadata_path: Optional[Path] = None,
        uploads_dir: Optional[Path] = None,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        self.metadata_path = metadata_path or root / "data" / "books.json"
        self.uploads_dir = uploads_dir or root / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def list_books(self) -> List[BookListItem]:
        records = self._load_metadata()
        return [BookListItem(**self._to_public_record(record)) for record in records]

    def get_book(self, book_id: str) -> BookDetails:
        record = self._find_record(book_id)
        return BookDetails(**self._to_public_record(record))

    def read_book(self, book_id: str) -> tuple[str, int, int]:
        record = self._find_record(book_id)
        file_path = record.get("file_path")
        if not file_path:
            raise ValueError("Book file path is missing.")
        file_format = record.get("format") or self._detect_format(Path(file_path))
        text, _page_count = self._extract_text(
            Path(file_path),
            file_format,
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
        book_id = uuid4().hex
        destination = self.uploads_dir / f"{book_id}{source_path.suffix.lower()}"
        shutil.copyfile(source_path, destination)

        text, page_count = self._extract_text(
            destination,
            file_format,
            preserve_format=False,
        )
        word_count = self._count_words(text)
        total_chunks = self._count_chunks(text)

        record: Dict[str, Any] = {
            "id": book_id,
            "title": title,
            "author": author,
            "description": description,
            "language": language,
            "format": file_format,
            "page_count": page_count,
            "word_count": word_count,
            "total_chunks": total_chunks,
            "created_at": datetime.utcnow().isoformat(),
            "file_path": str(destination),
        }

        records = self._load_metadata()
        records.append(record)
        self._save_metadata(records)

        return BookDetails(**self._to_public_record(record))

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

    def _extract_pdf_text(self, path: Path, preserve_format: bool = False) -> tuple[str, Optional[int]]:
        try:
            import pdfplumber
        except ImportError as exc:
            raise ValueError("pdfplumber is required to extract PDF text.") from exc

        texts: List[str] = []
        with pdfplumber.open(path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                if preserve_format:
                    try:
                        page_text = page.extract_text(
                            layout=True,
                            x_tolerance=2,
                            y_tolerance=2,
                        ) or ""
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

    def _extract_epub_text(self, path: Path, preserve_format: bool = False) -> tuple[str, Optional[int]]:
        try:
            from ebooklib import ITEM_DOCUMENT, epub
        except ImportError as exc:
            raise ValueError("ebooklib is required to extract EPUB text.") from exc

        book = epub.read_epub(str(path))
        texts: List[str] = []
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
        lines: List[List[dict]] = []
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

    def _load_metadata(self) -> List[Dict[str, Any]]:
        if not self.metadata_path.exists():
            return []
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError("books.json must contain a list.")
        return data

    def _save_metadata(self, records: List[Dict[str, Any]]) -> None:
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with self.metadata_path.open("w", encoding="utf-8") as handle:
            json.dump(records, handle, indent=2, sort_keys=True)

    def _find_record(self, book_id: str) -> Dict[str, Any]:
        records = self._load_metadata()
        for record in records:
            if record.get("id") == book_id:
                return record
        raise ValueError(f"Book {book_id} not found.")

    def _to_public_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        if record.get("created_at"):
            try:
                record = dict(record)
                record["created_at"] = datetime.fromisoformat(record["created_at"])
            except ValueError:
                pass
        record.pop("file_path", None)
        return record


_service: Optional[BookService] = None


def get_books_service() -> BookService:
    global _service
    if _service is None:
        _service = BookService()
    return _service
