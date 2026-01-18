# learnai-backend-app

Backend service for LearnAI.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Copy `.env.example` to `.env` and set required environment variables.

## Development

### Running the app

1. Create and activate a virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
4. Start the server:
   `uvicorn app.main:app --reload`

### Tooling

Install dev tools:
`pip install -r requirements-dev.txt`

Run linting:
`ruff check .`
`black --check .`
`mypy app tests`

Format code:
`ruff format .`
`black .`

Set up pre-commit hooks:
`pre-commit install`

Pre-commit will block commits and pushes if linting, mypy, or tests fail.
