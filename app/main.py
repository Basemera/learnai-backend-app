from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import engine
from app.models import (
    book,  # noqa: F401 – register model for create_all
    embedding,  # noqa: F401 – register embedding models for create_all
)
from app.models.base import Base
from app.routes.ai import router as ai_router
from app.routes.books import router as books_router

Base.metadata.create_all(bind=engine)  # create tables based on models
app = FastAPI(title="LearnAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(ai_router)
app.include_router(books_router)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}
