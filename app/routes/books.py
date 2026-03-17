import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from app.repositories.books_repository import BooksRepository
from sqlalchemy.orm import Session

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, BackgroundTasks, Depends

from app.schemas.books import BookDetails, BookListItem, BookReadResponse
from app.services.books_service import BookService, get_books_service
from app.services.embedding_service import EmbeddingsService, get_embeddings_service
from app.db import get_db

router = APIRouter(prefix="/books", tags=["books"])

def get_book_service(db: Session = Depends(get_db)) -> BookService:
    repo = BooksRepository(db)
    return BookService(repo=repo)

def get_embedding_service(db: Session = Depends(get_db)) -> EmbeddingsService:
    repo = BooksRepository(db)
    return EmbeddingsService(repo=repo)

@router.get("/", response_model=List[BookListItem])
def get_book(service: BookService = Depends(get_book_service)) -> List[BookListItem]:
    return service.list_books()


@router.get("/{book_id}", response_model=BookDetails)
def get_book_details(book_id: str, service: BookService = Depends(get_book_service)) -> BookDetails:
    try:
        return service.get_book(book_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{book_id}/read", response_model=BookReadResponse)
def read_book(book_id: str, service: BookService = Depends(get_book_service)) -> BookReadResponse:
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
    service: BookService = Depends(get_book_service),
    embedding_service: EmbeddingsService = Depends(get_embedding_service),
) -> BookDetails:
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
        background_tasks.add_task(embedding_service.index_book, details.id)
        return details
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

