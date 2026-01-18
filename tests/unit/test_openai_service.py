import sys
from types import SimpleNamespace
from typing import Optional

import pytest

from app.services.openai_service import OpenAIService


class DummyResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


class DummyResponses:
    def __init__(self) -> None:
        self.last_model: Optional[str] = None
        self.last_input: Optional[str] = None

    def create(self, model: str, input: str) -> DummyResponse:
        self.last_model = model
        self.last_input = input
        return DummyResponse(output_text="ok")


class DummyClient:
    def __init__(self) -> None:
        self.responses = DummyResponses()


def test_openai_service_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        OpenAIService(api_key=None)


def test_simplify_text_builds_prompt(monkeypatch) -> None:
    dummy_client = DummyClient()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda api_key: dummy_client))

    service = OpenAIService()
    result = service.simplify_text("hello")

    assert result == "ok"
    last_input = dummy_client.responses.last_input
    assert last_input is not None
    assert "Simplify" in last_input
    assert "hello" in last_input


def test_explain_text_builds_prompt(monkeypatch) -> None:
    dummy_client = DummyClient()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda api_key: dummy_client))

    service = OpenAIService()
    result = service.explain_text("hello")

    assert result == "ok"
    last_input = dummy_client.responses.last_input
    assert last_input is not None
    assert "Explain" in last_input
    assert "hello" in last_input
