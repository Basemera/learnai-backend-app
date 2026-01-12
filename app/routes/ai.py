from fastapi import APIRouter, HTTPException

from app.schemas.ai import TextRequest, TextResponse
from app.services.openai_service import get_openai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/simplify", response_model=TextResponse)
def simplify_text(payload: TextRequest) -> TextResponse:
    service = get_openai_service()
    try:
        result = service.simplify_text(payload.text)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="AI request failed.") from exc
    return TextResponse(result=result)


@router.post("/explain", response_model=TextResponse)
def explain_text(payload: TextRequest) -> TextResponse:
    service = get_openai_service()
    try:
        result = service.explain_text(payload.text)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="AI request failed.") from exc
    return TextResponse(result=result)
