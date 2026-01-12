# Agent Instructions

- Use concise, direct communication.
- Prefer `rg` for search.
- Avoid destructive git commands unless explicitly requested.
- Keep changes minimal and scoped to the request.
- Ask for clarification when requirements are ambiguous.

# LearnAI — Codex Instructions

## Product vision
This project is an AI-powered learning platform where:
- Students read ebooks inside the web app
- They can select text and ask AI to simplify, explain, or expand it
- The system can suggest and improve prompts
- Students get flashcards and quizzes generated from what they read
- The platform tracks progress, strengths, and weaknesses

The goal is to build this incrementally as a portfolio-grade AI learning system.

---

## Tech stack
Backend:
- Python
- FastAPI
- OpenAI API (Phase 1–3)
- PostgreSQL + SQLAlchemy (Phase 2+)
- Vector DB (Chroma first, Pinecone later)

Frontend:
- React (web-first)
- Axios or Fetch for API calls

---

## Phase 1 scope
Right now we are building:
- GET /health
- POST /ai/simplify
- POST /ai/explain

These endpoints must:
- Validate input with Pydantic
- Call OpenAI only via a service layer
- Return clean JSON responses

---

## Architecture rules
- No OpenAI calls inside routes
- All AI calls must go through app/services/openai_service.py
- All request/response schemas go in app/schemas
- Routes only handle HTTP and validation
- Business logic goes in services

---

## Prompt design
When generating prompts:
- Use simple educational tone
- Avoid hallucinations
- Prefer clarity over verbosity
- Assume the user is a student

---

## Coding standards
- Use clear, readable Python
- No massive functions
- Handle errors with HTTPException
- Don’t refactor unrelated code
- When modifying code, keep changes minimal and focused

---

## How Codex should behave
Before making changes:
- Briefly describe the plan

After making changes:
- Explain what was done
- Explain how to test it

## Commands
- Run API: uvicorn app.main:app --reload
- Lint (if present): ruff check .
- Format (if present): ruff format .

## How to work
- Before making changes: summarize plan in 3-6 bullets
- After changes: explain what changed and how to test
- Prefer minimal diffs; don’t refactor unrelated code
