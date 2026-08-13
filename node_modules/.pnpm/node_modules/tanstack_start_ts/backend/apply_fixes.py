import re
from pathlib import Path

# Fix 1: agent.py - garantir que cliente autenticado não caia no fluxo de CPF
path_agent = Path("backend/app/services/agent.py")
text = path_agent.read_text(encoding="utf-8")

# Verifica se já tem o bloco do autenticado no início
if "if authenticated:" not in text:
    # Insere o bloco autenticado logo após a definição de authenticated
    mark = "    # --- Cliente NÃO autenticado: fluxo de coleta e validação ---"
    block = '''    # --- Cliente autenticado: identifica o assunto e redireciona ---
    if authenticated:
        intent = _llm_intent(message, session.history) or detect_intent(message)
        session.pending_intent = intent
        print(f"[TRIAGEM] Assunto identificado: {intent}")

        if intent == "error":
            msg = "Entendi, estamos enfrentando uma instabilidade. Tente novamente em instantes."
            session.add_message("assistant", msg)
            return build_response(
                session.id,
                msg,
                "error",
                True,
                {"agent": "triage", "widget": {"kind": "error", "error": MOCK_SERVICE_ERROR}},
            )

        if intent == "closing":
            msg = "Foi um prazer ajudar. Sempre que precisar, estaremos por aqui."
            session.add_message("assistant", msg)
            return build_response(
                session.id,
                msg,
                "completed",
                True,
                {"agent": "triage", "widget": {"kind": "closing"}},
            )

        if intent in ("credit_limit", "credit_increase"):
            return handle_credit_message(session, message, intent)

        return _handle_authenticated_intent(session, intent, message)

'''
    text = text.replace(mark, block + mark)
    path_agent.write_text(text, encoding="utf-8")
    print("✅ agent.py: fluxo autenticado adicionado")
else:
    print("⚠️ agent.py: fluxo autenticado já existe")

# Fix 2: credit_service.py - garantir import de update_client_limits
path_credit = Path("backend/app/services/credit_service.py")
credit = path_credit.read_text(encoding="utf-8")
if "from app.services.client_db import update_client_limits, get_clients" not in credit:
    credit = credit.replace(
        "from app.services.client_db import get_clients",
        "from app.services.client_db import update_client_limits, get_clients"
    )
    path_credit.write_text(credit, encoding="utf-8")
    print("✅ credit_service.py: import update_client_limits adicionado")
else:
    print("⚠️ credit_service.py: import já existe")