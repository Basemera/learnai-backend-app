from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ai import router as ai_router


app = FastAPI(title="LearnAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}
