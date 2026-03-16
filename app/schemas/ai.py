from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class TextRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=20_000,
        description="User-provided text.",
    )


class TextResponse(BaseModel):
    result: str


class ExplainRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=20_000,
        description="User-provided text to explain.",
    )

    audience: str = Field(
        "a student",
        min_length=1,
        max_length=120,
        description="Target audience (e.g., 'a beginner', 'a high school student').",
    )
    difficulty: str = Field(
        "simple",
        min_length=1,
        max_length=40,
        description="Difficulty level (e.g., 'simple', 'intermediate').",
    )
    tone: str = Field(
        "friendly and clear",
        min_length=1,
        max_length=80,
        description="Tone of the explanation.",
    )
    format: Literal["structured", "prose"] = Field(
        "structured",
        description="Preferred output format.",
    )
    max_bullets: int = Field(6, ge=1, le=20, description="Maximum number of bullet points.")
    include_examples: bool = Field(True, description="Whether to include an example.")
    include_key_terms: bool = Field(True, description="Whether to include key terms definitions.")
    include_questions: bool = Field(True, description="Whether to include check-understanding questions.")


class ExplainKeyTerm(BaseModel):
    term: str
    definition: str


class ExplainPayload(BaseModel):
    one_sentence_summary: str
    bullet_points: List[str]
    key_terms: Optional[List[ExplainKeyTerm]] = None
    example: Optional[str] = None
    check_understanding: Optional[List[str]] = None


class ExplainResponse(BaseModel):
    result: ExplainPayload


GradeLevel = Literal["elementary", "middle_school", "high_school", "college"]
Tone = Literal["clear", "friendly", "formal"]
OutputFormat = Literal["structured_json", "bullets", "paragraph"]

class SimplifyRequest(BaseModel):
    text: str = Field(..., min_length=1, description="User-provided text.")

    grade_level: GradeLevel = "middle_school"
    tone: Tone = "clear"
    format: OutputFormat = "structured_json"

    max_sentences: int = Field(3, ge=1, le=10)
    keep_key_terms: bool = True
    define_key_terms: bool = True
    max_definitions: int = Field(6, ge=0, le=15)