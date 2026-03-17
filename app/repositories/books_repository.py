from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.book import Book


class BooksRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_books(self) -> List[Book]:
        stmt = select(Book).order_by(Book.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_book(self, book_id: str) -> Optional[Book]:
        return self.db.get(Book, book_id)

    def create_book(self, book: Book) -> Book:
        self.db.add(book)
        self.db.commit()
        self.db.refresh(book)
        return book