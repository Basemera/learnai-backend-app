# Summary

- decouple app startup from eager database initialization so the app can import without a configured DB
- align `/ai/simplify` with a structured JSON response contract and validate it with Pydantic
- remove stale metadata-file helpers from `BookService`
- update local and unit tests to match the current route behavior and dependency injection
- fix repo-wide CI issues across Ruff, Black, mypy, and pytest
- preserve Python 3.9 compatibility for SQLAlchemy model annotations while keeping the lint config aligned with that runtime target

# Testing

- `learningai_be_venv/bin/pytest tests/local/test_ai_routes.py tests/local/test_books_routes.py tests/unit/test_openai_service.py tests/unit/test_books_service.py tests/unit/test_embedding_service.py`
- `learningai_be_venv/bin/ruff check app/db.py app/main.py app/routes/ai.py app/schemas/ai.py app/services/books_service.py tests/local/test_ai_routes.py tests/local/test_books_routes.py tests/unit/test_openai_service.py`
- `learningai_be_venv/bin/ruff check .`
- `learningai_be_venv/bin/black --check .`
- `learningai_be_venv/bin/mypy app tests`
- `learningai_be_venv/bin/pytest tests/unit tests/local`
