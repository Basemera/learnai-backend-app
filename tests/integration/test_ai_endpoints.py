import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="Integration tests require RUN_INTEGRATION_TESTS=1 and real API keys.",
)
def test_simplify_text_integration() -> None:
    client = TestClient(app)
    response = client.post("/ai/simplify", json={"text": "Test"})
    assert response.status_code == 200
    assert "result" in response.json()


@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="Integration tests require RUN_INTEGRATION_TESTS=1 and real API keys.",
)
def test_explain_text_integration() -> None:
    client = TestClient(app)
    response = client.post("/ai/explain", json={"text": "Test"})
    assert response.status_code == 200
    assert "result" in response.json()
