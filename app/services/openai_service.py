import os
from typing import Optional

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled in environments without openai
    OpenAI = None


class OpenAIService:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini") -> None:
        if OpenAI is None:
            raise ValueError("openai package is not installed.")
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _call_model(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        return response.output_text

    def simplify_text(self, text: str) -> str:
        prompt = (
            "You are a helpful tutor. Simplify the following text for a student "
            "while keeping the meaning intact:\n\n"
            f"{text}"
        )
        return self._call_model(prompt)

    def explain_text(self, text: str) -> str:
        prompt = (
            "You are a helpful tutor. Explain the following text in simple terms "
            "with clear, concise language:\n\n"
            f"{text}"
        )
        return self._call_model(prompt)


_service: Optional[OpenAIService] = None


def get_openai_service() -> OpenAIService:
    global _service
    if _service is None:
        _service = OpenAIService()
    return _service
