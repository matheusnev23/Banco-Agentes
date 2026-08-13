"""Schemas da entrevista financeira."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

QuestionKind = Literal["currency", "number", "text", "choice"]


class InterviewQuestion(BaseModel):
    """Pergunta da entrevista financeira."""

    id: str
    label: str
    kind: QuestionKind
    placeholder: Optional[str] = None
    options: Optional[list[str]] = None
    answer: Optional[str] = None


class InterviewSubmitRequest(BaseModel):
    """Corpo de `POST /api/interview`."""

    session_id: str
    answers: dict[str, str] = Field(..., description="Respostas por ID da pergunta")


class CreditScore(BaseModel):
    """Score de crédito do cliente."""

    value: int
    max: int = 1000
    band: Literal["low", "medium", "high"]
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class InterviewResponse(BaseModel):
    """Resposta de `POST /api/interview`."""

    score: CreditScore
    questions: list[InterviewQuestion]