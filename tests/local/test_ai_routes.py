import json

from fastapi.testclient import TestClient

from app.main import app
from app.routes import ai as ai_routes


class DummyAIService:
    def simplify_text(self, text: str, **_: object) -> str:
        return json.dumps(
            {
                "simplified": f"simplified: {text}",
                "bullets": ["first"],
                "key_terms": [{"term": "term", "definition": "meaning"}],
                "notes": "note",
            }
        )

    def explain_text(self, text: str, **_: object) -> str:
        return json.dumps(
            {
                "one_sentence_summary": f"explained: {text}",
                "bullet_points": ["point"],
                "key_terms": [{"term": "term", "definition": "meaning"}],
                "example": "example",
                "check_understanding": ["question"],
            }
        )


def test_health_check() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_simplify_text(monkeypatch) -> None:
    monkeypatch.setattr(ai_routes, "get_openai_service", lambda: DummyAIService())
    client = TestClient(app)
    response = client.post("/ai/simplify", json={"text": "Test"})
    assert response.status_code == 200
    assert response.json() == {
        "result": {
            "simplified": "simplified: Test",
            "bullets": ["first"],
            "key_terms": [{"term": "term", "definition": "meaning"}],
            "notes": "note",
        }
    }


def test_explain_text(monkeypatch) -> None:
    monkeypatch.setattr(ai_routes, "get_openai_service", lambda: DummyAIService())
    client = TestClient(app)
    response = client.post("/ai/explain", json={"text": "Test"})
    assert response.status_code == 200
    assert response.json() == {
        "result": {
            "one_sentence_summary": "explained: Test",
            "bullet_points": ["point"],
            "key_terms": [{"term": "term", "definition": "meaning"}],
            "example": "example",
            "check_understanding": ["question"],
        }
    }


def test_validation_error_on_empty_text() -> None:
    client = TestClient(app)
    response = client.post("/ai/explain", json={"text": ""})
    assert response.status_code == 422
