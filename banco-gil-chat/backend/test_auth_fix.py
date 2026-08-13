"""Teste para validar o fix de autenticação.

Verifica cenários:
1. Dados parciais limpos após falha (CPF errado + data correta → falha → limpa)
2. Corrigir só CPF não autentica (sem data reenviada)
3. CPF + data corretos juntos autenticam
4. Enviar data primeiro, depois CPF separadamente → autentica (parciais funcionam)
5. Enviar CPF errado + data, corrigir CPF → pede data de novo (parciais limpos)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.models.session import session_store
from app.services.agent import handle_message, MAX_AUTH_ATTEMPTS


def _start_auth_session(intent="credit_limit"):
    """Cria uma sessão e entra no fluxo de autenticação."""
    session = session_store.create()
    session._authenticating = True
    session.pending_intent = intent
    return session


def test_partial_data_cleared_after_failure():
    """Dados parciais devem ser limpos após falha na autenticação."""
    print("\n=== TESTE 1: Limpeza de dados parciais após falha ===")

    session = _start_auth_session()

    # 1. CPF errado + data correta → falha
    handle_message(session, "123.456.789-00 15/03/1988")
    print(f"  Tentativa 1 (CPF errado): _partial_cpf={session._partial_cpf}, _partial_birth={session._partial_birth}")
    assert session._partial_cpf is None, "CPF deveria ser limpo após falha"
    assert session._partial_birth is None, "Data deveria ser limpa após falha"
    assert session.client is None
    assert session.auth_attempts == 1

    # 2. Corrige só o CPF → não autentica (data foi limpa)
    handle_message(session, "111.444.777-35")
    print(f"  Tentativa 2 (CPF corrigido): _partial_cpf={session._partial_cpf}, _partial_birth={session._partial_birth}")
    assert session.client is None, "Não deveria autenticar sem data"
    assert session._partial_birth is None

    # 3. Envia data correta também → autentica
    handle_message(session, "15/03/1988")
    print(f"  Tentativa 3 (CPF + data): client={session.client.name if session.client else None}")
    assert session.client is not None, "Deveria estar autenticado"
    assert session.status == "authenticated"

    print("✅ PASSOU!")


def test_date_first_then_cpf():
    """Enviar data de nascimento primeiro, depois CPF separadamente NÃO deve autenticar.

    A ordem correta é: primeiro o CPF, depois a data de nascimento.
    A data enviada antes do CPF deve ser IGNORADA.
    """
    print("\n=== TESTE 2: Data primeiro é ignorada — CPF exigido primeiro ===")

    session = _start_auth_session()

    # 1. Usuário envia apenas a data de nascimento (fora da ordem)
    handle_message(session, "23122003")
    print(f"  Tentativa 1 (data só): _partial_cpf={session._partial_cpf}, _partial_birth={session._partial_birth}")
    assert session._partial_birth is None, "Data enviada antes do CPF deveria ser IGNORADA"
    assert session._partial_cpf is None, "CPF deveria ser None ainda"
    assert session.client is None, "Não deveria estar autenticado"

    # 2. Usuário envia o CPF (agora sim, é armazenado)
    handle_message(session, "45573022890")
    print(f"  Tentativa 2 (CPF só): _partial_cpf={session._partial_cpf}, _partial_birth={session._partial_birth}")
    assert session._partial_cpf == "45573022890", "CPF deveria estar armazenado"
    assert session._partial_birth is None, "Data ainda não deveria estar armazenada (foi ignorada)"
    assert session.client is None, "Não deveria estar autenticado ainda (falta a data)"

    # 3. Agora envia a data de nascimento (na ordem correta)
    handle_message(session, "23122003")
    print(f"  Tentativa 3 (data): _partial_cpf={session._partial_cpf}, _partial_birth={session._partial_birth}")
    assert session.client is not None, "Deveria estar autenticado com CPF + data"
    assert session.status == "authenticated"
    print(f"  Cliente: {session.client.name}")

    print("✅ PASSOU!")


def test_wrong_cpf_correct_date_then_fix_both():
    """CPF errado + data correta falha, depois envia ambos corretos juntos."""
    print("\n=== TESTE 3: CPF errado + data, depois ambos corretos ===")

    session = _start_auth_session()

    # 1. CPF errado + data correta → falha
    handle_message(session, "999.999.999-99 23/12/2003")
    print(f"  Tentativa 1 (CPF errado): _partial_cpf={session._partial_cpf}, _partial_birth={session._partial_birth}")
    assert session.client is None
    assert session._partial_cpf is None, "Parciais deveriam ser limpos"
    assert session._partial_birth is None
    assert session.auth_attempts == 1

    # 2. Envia CPF correto + data correta juntos
    handle_message(session, "45573022890 23/12/2003")
    print(f"  Tentativa 2 (ambos corretos): client={session.client.name if session.client else None}")
    assert session.client is not None, "Deveria autenticar"
    assert session.status == "authenticated"

    print("✅ PASSOU!")


def test_both_correct_first_try():
    """CPF + data corretos na primeira tentativa."""
    print("\n=== TESTE 4: Ambos corretos na primeira tentativa ===")

    session = _start_auth_session()
    handle_message(session, "111.444.777-35 15/03/1988")
    print(f"  Resultado: client={session.client.name if session.client else None}")
    assert session.client is not None
    assert session.status == "authenticated"
    assert session.auth_attempts == 0

    print("✅ PASSOU!")


if __name__ == "__main__":
    test_partial_data_cleared_after_failure()
    test_date_first_then_cpf()
    test_wrong_cpf_correct_date_then_fix_both()
    test_both_correct_first_try()
    print("\n🎉 Todos os testes de autenticação passaram!")
