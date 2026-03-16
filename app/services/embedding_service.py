import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.openai_service import get_openai_service


@dataclass(frozen=True)
class EmbeddingChunk:
    chunk_index: int
    text: str
    embedding: List[float]


class EmbeddingsService:
    def __init__(
        self,
        metadata_path: Optional[Path] = None,
        embeddings_dir: Optional[Path] = None,
        embedding_model: str = "text-embedding-3-small",
        chunk_size_words: int = 400,
        overlap_words: int = 50,
        batch_size: int = 64,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        self.metadata_path = metadata_path or root / "data" / "books.json"
        self.embeddings_dir = embeddings_dir or root / "data" / "embeddings"
        self.embedding_model = embedding_model
        self.chunk_size_words = chunk_size_words
        self.overlap_words = overlap_words
        self.batch_size = batch_size

    def index_book(self, book_id: str) -> None:
        """
        Background task entrypoint. Writes:
          data/embeddings/{book_id}.json
        with status: pending -> ready/failed.
        """
        record = self._find_book_record(book_id)
        file_path = record.get("file_path")
        if not file_path:
            # Can't proceed; write failed status so callers can see it.
            self._write_embeddings_file(book_id, status="failed", error="Book file path is missing.")
            return

        self._write_embeddings_file(book_id, status="pending")

        try:
            text = self._extract_book_text(Path(file_path), file_format=record.get("format"), preserve_format=True)
            chunks = self._chunk_text_words(text)

            embeddings = self._embed_chunks([c["text"] for c in chunks])
            chunk_records: List[Dict[str, Any]] = []
            for i, chunk in enumerate(chunks):
                chunk_records.append(
                    {
                        "chunk_index": chunk["chunk_index"],
                        "text": chunk["text"],
                        "embedding": embeddings[i],
                    }
                )

            payload = {
                "book_id": book_id,
                "status": "ready",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "embedding_model": self.embedding_model,
                "chunk_size_words": self.chunk_size_words,
                "overlap_words": self.overlap_words,
                "chunks": chunk_records,
            }
            self._save_json(self._embeddings_path(book_id), payload)
        except Exception as exc:
            self._write_embeddings_file(book_id, status="failed", error=str(exc))

    # -------- internals --------

    def _embeddings_path(self, book_id: str) -> Path:
        return self.embeddings_dir / f"{book_id}.json"

    def _write_embeddings_file(self, book_id: str, *, status: str, error: Optional[str] = None) -> None:
        payload: Dict[str, Any] = {
            "book_id": book_id,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if error:
            payload["error"] = error
        self._save_json(self._embeddings_path(book_id), payload)

    def _save_json(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    def _load_metadata(self) -> List[Dict[str, Any]]:
        if not self.metadata_path.exists():
            return []
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError("books.json must contain a list.")
        return data

    def _find_book_record(self, book_id: str) -> Dict[str, Any]:
        for record in self._load_metadata():
            if record.get("id") == book_id:
                return record
        raise ValueError(f"Book {book_id} not found.")

    def _extract_book_text(self, path: Path, *, file_format: Optional[str], preserve_format: bool) -> str:
        # Reuse BookService extraction by instantiating and calling its internals (minimal duplication).
        # Alternative is to refactor BookService to share a TextExtractor, but this keeps diff small.
        from app.services.books_service import BookService

        service = BookService(metadata_path=self.metadata_path, uploads_dir=path.parent)
        fmt = file_format or service._detect_format(path)  # type: ignore[attr-defined]
        text, _page_count = service._extract_text(path, fmt, preserve_format=preserve_format)  # type: ignore[attr-defined]
        return text

    def _chunk_text_words(self, text: str) -> List[Dict[str, Any]]:
        if not text:
            return []
        words = text.split()
        chunks: List[Dict[str, Any]] = []
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

    def _embed_chunks(self, chunk_texts: List[str]) -> List[List[float]]:
        if not chunk_texts:
            return []
        service = get_openai_service()
        vectors: List[List[float]] = []
        for start in range(0, len(chunk_texts), self.batch_size):
            batch = chunk_texts[start : start + self.batch_size]
            vectors.extend(service.embed_texts(batch, model=self.embedding_model))
        return vectors


_service: Optional[EmbeddingsService] = None


def get_embeddings_service() -> EmbeddingsService:
    global _service
    if _service is None:
        _service = EmbeddingsService()
    return _service