from pydantic import BaseModel, Field


class TextRequest(BaseModel):
    text: str = Field(..., min_length=1, description="User-provided text.")


class TextResponse(BaseModel):
    result: str
