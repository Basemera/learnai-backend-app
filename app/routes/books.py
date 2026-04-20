from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories.books_repository import BooksRepository
from app.repositories.embeddings_repository import EmbeddingsRepository
from app.schemas.books import BookDetails, BookListItem, BookReadResponse
from app.services.books_service import BookService
from app.services.embedding_service import EmbeddingsService

router = APIRouter(prefix="/books", tags=["books"])


def get_book_service(db: Session = Depends(get_db)) -> BookService:
    repo = BooksRepository(db)
    return BookService(repo=repo)


def get_embedding_service(db: Session = Depends(get_db)) -> EmbeddingsService:
    books_repo = BooksRepository(db)
    embeddings_repo = EmbeddingsRepository(db)
    return EmbeddingsService(books_repo=books_repo, embeddings_repo=embeddings_repo)


@router.get("/", response_model=list[BookListItem])
def get_book(service: BookService = Depends(get_book_service)) -> list[BookListItem]:
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
            temp_file.write(file.file.read())
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
