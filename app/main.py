from typing import Any, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ai import router as ai_router
from app.routes.books import router as books_router

app = FastAPI(title="LearnAI API")

app.add_middleware(
    cast(Any, CORSMiddleware),
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
