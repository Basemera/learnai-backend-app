from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BookListItem(BaseModel):
    id: str
    title: str = Field(..., min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    format: Optional[str] = Field(None, description="File type, e.g., pdf or epub.")
    progress_percent: Optional[float] = Field(None, ge=0, le=100)


class BookDetails(BaseModel):
    id: str
    title: str = Field(..., min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    language: Optional[str] = Field(None, min_length=2, max_length=16)
    format: Optional[str] = Field(None, description="File type, e.g., pdf or epub.")
    page_count: Optional[int] = Field(None, ge=1)
    word_count: Optional[int] = Field(None, ge=1)
    total_chunks: Optional[int] = Field(None, ge=0)
    created_at: Optional[datetime] = None
