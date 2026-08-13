"""Teste do fluxo de aumento de limite com formato brasileiro."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.models.session import session_store
from app.schemas.auth import Client
from app.services.credit_service import request_credit_increase, get_credit_limit
from app.agents.credit_agent import _extract_requested_limit, _is_additional_increase


def main():
    # Limpa sessões anteriores
    session_store._sessions.clear()

    # Simula sessão do Matheus Neves com limite 20000
    session = session_store.create()
    session.client = Client(
        id="test_client",
        name="Matheus Neves",
        masked_document="***.***.***-90",
        limite_total=20000.0,
        limite_disponivel=20000.0,
    )
    session.client_cpf = "45573022890"
    session.status = "authenticated"

    # Cenário 1: "quero mais 2.000 de limite" (aumento adicional)
    message = "quero mais 2.000 de limite"
    requested = _extract_requested_limit(message)
    is_add = _is_additional_increase(message)
    print(f'Cenário 1: "{message}"')
    print(f"  Valor extraído: {requested}")
    print(f"  É aumento adicional: {is_add}")

    # Consulta o banco primeiro
    limit = get_credit_limit(session.id)
    print(f"  Limite atual do banco: {limit.total}")

    # Se for adicional, soma ao limite atual
    if is_add:
        requested = limit.total + requested
        print(f"  Novo limite calculado: {requested}")

    result = request_credit_increase(session.id, requested)
    print(f"  Status: {result.status}")
    print(f"  Novo total: {result.new_total}")

    # Verifica o banco
    limit_after = get_credit_limit(session.id)
    print(f"  Limite no banco após: {limit_after.total}")
    print()

    # Cenário 2: "quero aumentar para 22.000" (novo limite total)
    message2 = "quero aumentar para 22.000"
    requested2 = _extract_requested_limit(message2)
    is_add2 = _is_additional_increase(message2)
    print(f'Cenário 2: "{message2}"')
    print(f"  Valor extraído: {requested2}")
    print(f"  É aumento adicional: {is_add2}")
    print(f"  Novo limite: {requested2}")


if __name__ == "__main__":
    main()