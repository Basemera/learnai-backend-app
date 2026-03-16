import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, BackgroundTasks

from app.schemas.books import BookDetails, BookListItem, BookReadResponse
from app.services.books_service import get_books_service
from app.services.embedding_service import get_embeddings_service

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/", response_model=List[BookListItem])
def get_book() -> List[BookListItem]:
    service = get_books_service()
    return service.list_books()


@router.get("/{book_id}", response_model=BookDetails)
def get_book_details(book_id: str) -> BookDetails:
    service = get_books_service()
    try:
        return service.get_book(book_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{book_id}/read", response_model=BookReadResponse)
def read_book(book_id: str) -> BookReadResponse:
    service = get_books_service()
    try:
        text, word_count, total_chunks = service.read_book(book_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return BookReadResponse(
        id=book_id,
        text=text,
        word_count=word_count,
        total_chunks=total_chunks,
    )


@router.post("/upload", response_model=BookDetails)
def upload_book(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    author: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
) -> BookDetails:
    service = get_books_service()
    suffix = Path(file.filename or "").suffix
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        details = service.upload_book(
            file_path=temp_path,
            title=title,
            author=author,
            language=language,
            description=description,
        )
        embedding_service = get_embeddings_service()
        background_tasks.add_task(embedding_service.index_book, details.id)
        return details
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

