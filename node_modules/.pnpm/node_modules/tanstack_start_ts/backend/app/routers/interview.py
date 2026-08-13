"""Rotas da entrevista financeira."""

from fastapi import APIRouter, HTTPException

from app.models.session import session_store
from app.schemas.interview import InterviewQuestion, InterviewResponse, InterviewSubmitRequest
from app.services import interview_service

router = APIRouter()


@router.get("/interview/questions", response_model=list[InterviewQuestion])
async def get_interview_questions() -> list[InterviewQuestion]:
    """Retorna as perguntas da entrevista financeira."""
    return interview_service.get_questions()


@router.post("/interview", response_model=InterviewResponse)
async def submit_interview(payload: InterviewSubmitRequest) -> InterviewResponse:
    """Processa as respostas da entrevista e retorna o score."""
    session = session_store.get(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    if session.client is None:
        raise HTTPException(status_code=401, detail="Cliente não autenticado")
    return interview_service.submit_answers(payload.session_id, payload.answers)