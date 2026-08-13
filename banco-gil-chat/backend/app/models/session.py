"""Sessões de conversa em memória.

Por enquanto as sessões ficam em um dict simples. Quando houver banco de dados,
basta trocar esta implementação por uma persistência real (ex: SQLAlchemy + Postgres).
"""

import threading
import uuid
from datetime import datetime
from typing import Optional

from app.schemas.auth import Client
from app.schemas.chat import AgentState, ServiceStatus


class Session:
    """Sessão de conversa de um cliente."""

    def __init__(self, session_id: str) -> None:
        self.id = session_id
        self.status: ServiceStatus = "unauthenticated"
        self.agent: AgentState = "triage"
        self.active_agent: Optional[str] = None  # Agente atualmente em conversa (ex: "credit_interview")
        self.client: Optional[Client] = None
        self.client_cpf: Optional[str] = None  # CPF do cliente autenticado (para lookups no CSV)
        self.pending_intent: Optional[str] = None
        self.auth_attempts: int = 0
        self.history: list[dict[str, str]] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self._partial_cpf: Optional[str] = None
        self._partial_birth: Optional[str] = None

    def add_message(self, role: str, content: str) -> None:
        """Adiciona uma mensagem ao histórico da conversa."""
        self.history.append({"role": role, "content": content})
        self.updated_at = datetime.now().isoformat()


class SessionStore:
    """Armazenamento de sessões em memória (thread-safe)."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str) -> Session:
        """Retorna a sessão existente ou cria uma nova."""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = Session(session_id)
            return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[Session]:
        """Retorna a sessão ou None se não existir."""
        with self._lock:
            return self._sessions.get(session_id)

    def create(self) -> Session:
        """Cria uma nova sessão com ID gerado."""
        session_id = f"conv_{uuid.uuid4().hex[:8]}"
        return self.get_or_create(session_id)

    def delete(self, session_id: str) -> bool:
        """Remove uma sessão. Retorna True se existia."""
        with self._lock:
            return self._sessions.pop(session_id, None) is not None


session_store = SessionStore()
