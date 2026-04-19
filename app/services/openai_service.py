import logging
import os
from typing import Any, Optional, cast

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini") -> None:
        try:
            from openai import OpenAI as OpenAIClient
        except ImportError as exc:  # pragma: no cover - handled in environments without openai
            raise ValueError("openai package is not installed.") from exc

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        self.client = OpenAIClient(api_key=api_key)
        self.model = model

    def _call_model(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        output_text = cast(Optional[str], getattr(response, "output_text", None))
        if not output_text:
            raise ValueError("OpenAI response contained no output_text.")
        return output_text

    def _build_simplify_prompt(
        self,
        text: str,
        *,
        grade_level: str,
        tone: str,
        format: str,
        max_sentences: int,
        keep_key_terms: bool,
        define_key_terms: bool,
        max_definitions: int,
    ) -> str:
        return (
            "You are a helpful tutor.\n"
            "Task: Simplify the user's text while preserving meaning.\n\n"
            f"Target grade level: {grade_level}\n"
            f"Tone: {tone}\n"
            f"Output format: {format}\n"
            f"Max sentences (for simplified text): {max_sentences}\n"
            f"Keep key terms: {keep_key_terms}\n"
            f"Define key terms: {define_key_terms}\n"
            f"Max definitions: {max_definitions}\n\n"
            "Return JSON ONLY with this schema:\n"
            "{\n"
            '  "simplified": string,\n'
            '  "bullets": string[],\n'
            '  "key_terms": [{"term": string, "definition": string}],\n'
            '  "notes": string\n'
            "}\n\n"
            "User text:\n"
            f"{text}"
        )

    def simplify_text(
        self,
        text: str,
        *,
        grade_level: str = "middle_school",
        tone: str = "clear",
        format: str = "structured_json",
        max_sentences: int = 3,
        keep_key_terms: bool = True,
        define_key_terms: bool = True,
        max_definitions: int = 6,
    ) -> str:
        prompt = self._build_simplify_prompt(
            text,
            grade_level=grade_level,
            tone=tone,
            format=format,
            max_sentences=max_sentences,
            keep_key_terms=keep_key_terms,
            define_key_terms=define_key_terms,
            max_definitions=max_definitions,
        )
        return self._call_model(prompt)

    def _build_explain_prompt(
        self,
        text: str,
        *,
        audience: str = "a student",
        difficulty: str = "simple",
        tone: str = "friendly and clear",
        format: str = "structured",
        max_bullets: int = 6,
        include_examples: bool = True,
        include_key_terms: bool = True,
        include_questions: bool = True,
    ) -> str:
        safe_text = (text or "").strip()
        if not safe_text:
            raise ValueError("text is required")

        # Align with app/schemas/ai.py ExplainPayload keys.
        # We ask for JSON-only so the route can json.loads + validate with ExplainPayload.
        key_terms_line = (
            '- "key_terms": array of objects { "term": string, "definition": string }\n'
            if include_key_terms
            else '- "key_terms": null\n'
        )
        example_line = '- "example": string\n' if include_examples else '- "example": null\n'
        questions_line = (
            '- "check_understanding": array of 1-3 short questions\n'
            if include_questions
            else '- "check_understanding": null\n'
        )

        return (
            "You are a helpful tutor.\n\n"
            "Task: Explain the text below.\n"
            f"Audience: {audience}\n"
            f"Difficulty: {difficulty}\n"
            f"Tone: {tone}\n"
            f"Format: {format}\n\n"
            "Rules:\n"
            "- Preserve the original meaning.\n"
            "- Do not add new facts; if something is unclear, say it's unclear.\n"
            f"- Use at most {max_bullets} bullet points.\n"
            "- Output MUST be valid JSON only (no Markdown, no surrounding text).\n\n"
            "Output JSON with these keys exactly:\n"
            '- "one_sentence_summary": string\n'
            f'- "bullet_points": array of strings (max {max_bullets} items)\n'
            f"{key_terms_line}"
            f"{example_line}"
            f"{questions_line}\n"
            "Text:\n"
            f"{safe_text}"
        )

    def explain_text(
        self,
        text: str,
        *,
        audience: str = "a student",
        difficulty: str = "simple",
        tone: str = "friendly and clear",
        format: str = "structured",
        max_bullets: int = 6,
        include_examples: bool = True,
        include_key_terms: bool = True,
        include_questions: bool = True,
    ) -> str:
        prompt = self._build_explain_prompt(
            text,
            audience=audience,
            difficulty=difficulty,
            tone=tone,
            format=format,
            max_bullets=max_bullets,
            include_examples=include_examples,
            include_key_terms=include_key_terms,
            include_questions=include_questions,
        )
        return self._call_model(prompt)

    def embed_texts(
        self,
        texts: list[str],
        model: str = "text-embedding-3-small",
    ) -> list[list[float]]:
        if not texts:
            logger.warning("embed_texts called with empty texts list.")
            return []
        try:
            response: Any = self.client.embeddings.create(model=model, input=texts)
        except Exception as exc:
            logger.error(f"Error calling OpenAI embeddings API: {exc}")
            raise ValueError("Failed to get embeddings from OpenAI.") from exc
        data = getattr(response, "data", None)
        if data is None:
            raise ValueError("OpenAI embeddings response contained no data.")
        return [item.embedding for item in data]


_service: Optional[OpenAIService] = None


def get_openai_service() -> OpenAIService:
    global _service
    if _service is None:
        _service = OpenAIService()
    return _service
