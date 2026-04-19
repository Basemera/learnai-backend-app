from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    format: Mapped[str] = mapped_column(String(8), nullable=False)

    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
