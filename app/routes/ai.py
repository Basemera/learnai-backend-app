import json

from fastapi import APIRouter, HTTPException

from app.schemas.ai import (
    ExplainPayload,
    ExplainRequest,
    ExplainResponse,
    SimplifyPayload,
    SimplifyRequest,
    SimplifyResponse,
)
from app.services.openai_service import get_openai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/simplify", response_model=SimplifyResponse)
def simplify_text(payload: SimplifyRequest) -> SimplifyResponse:
    service = get_openai_service()
    try:
        raw = service.simplify_text(
            payload.text,
            grade_level=payload.grade_level,
            tone=payload.tone,
            format=payload.format,
            max_sentences=payload.max_sentences,
            keep_key_terms=payload.keep_key_terms,
            define_key_terms=payload.define_key_terms,
            max_definitions=payload.max_definitions,
        )

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail="AI returned invalid JSON for simplify.",
            ) from exc

        try:
            parsed = SimplifyPayload.model_validate(data)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail="AI returned JSON that does not match the expected simplify schema.",
            ) from exc

        return SimplifyResponse(result=parsed)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="AI request failed.") from exc


@router.post("/explain", response_model=ExplainResponse)
def explain_text(payload: ExplainRequest) -> ExplainResponse:
    service = get_openai_service()
    try:
        raw = service.explain_text(
            payload.text,
            audience=payload.audience,
            difficulty=payload.difficulty,
            tone=payload.tone,
            format=payload.format,
            max_bullets=payload.max_bullets,
            include_examples=payload.include_examples,
            include_key_terms=payload.include_key_terms,
            include_questions=payload.include_questions,
        )

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail="AI returned invalid JSON for explain.",
            ) from exc

        try:
            parsed = ExplainPayload.model_validate(data)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail="AI returned JSON that does not match the expected explain schema.",
            ) from exc

        return ExplainResponse(result=parsed)

    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="AI request failed.") from exc
