"""Rotas do chat."""

from fastapi import APIRouter

from app.models.session import session_store
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import agent

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def send_message(payload: ChatRequest) -> ChatResponse:
    """Processa uma mensagem do usuário e retorna a resposta do agente."""
    session = session_store.get_or_create(payload.session_id)
    return agent.handle_message(session, payload.message)


@router.post("/chat/start", response_model=dict)
async def start_conversation() -> dict:
    """Inicia uma nova conversa e retorna o ID da sessão."""
    session = session_store.create()
    return {"session_id": session.id}