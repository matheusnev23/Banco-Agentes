"""Testes rápidos para o agente de entrevista de crédito."""

import sys
from pathlib import Path

# Adiciona o diretório backend ao path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.agents.credit_interview_agent import (
    _calculate_score,
    _parse_br_number,
    _update_client_score,
    _get_client_row,
)
from app.models.session import session_store
from app.schemas.auth import Client
from app.agents.credit_interview_agent import handle_interview


def create_test_session(cpf: str = "45573022890"):
    """Cria uma sessão de teste com cliente autenticado."""
    session = session_store.create()
    session.client = Client(
        id="test_client",
        name="Matheus Neves",
        masked_document="***.***.***-90",
        limite_total=30000.0,
        limite_disponivel=30000.0,
    )
    session.client_cpf = cpf
    session.status = "authenticated"
    return session


def test_parse_br_number():
    """Testa o parser de números brasileiros."""
    print("\n=== TESTE: PARSE DE NÚMEROS ===")
    assert _parse_br_number("2000") == 2000.0
    assert _parse_br_number("2.000") == 2000.0
    assert _parse_br_number("2.000,50") == 2000.5
    assert _parse_br_number("2,5") == 2.5
    assert _parse_br_number("R$ 2.000") == 2000.0
    assert _parse_br_number("15k") == 15000.0
    assert _parse_br_number("15K") == 15000.0
    print("✅ Parse de números funcionou!")


def test_calculate_score():
    """Testa o cálculo do score."""
    print("\n=== TESTE: CÁLCULO DE SCORE ===")
    
    # Teste 1: Renda alta, despesas baixas, emprego formal, sem dependentes, sem dívidas
    score = _calculate_score(renda=5000, despesas=1000, tipo_emprego="CLT", dependentes=0, tem_dividas=False)
    print(f"Score 1: {score}")
    assert 0 <= score <= 1000, f"Score fora do intervalo: {score}"
    
    # Teste 2: Renda baixa, despesas altas, desempregado, 3+ dependentes, com dívidas
    score = _calculate_score(renda=1000, despesas=2000, tipo_emprego="desempregado", dependentes=4, tem_dividas=True)
    print(f"Score 2: {score}")
    assert 0 <= score <= 1000, f"Score fora do intervalo: {score}"
    
    # Teste 3: Autônomo, sem dívidas
    score = _calculate_score(renda=3000, despesas=1500, tipo_emprego="Autônomo", dependentes=1, tem_dividas=False)
    print(f"Score 3: {score}")
    assert 0 <= score <= 1000, f"Score fora do intervalo: {score}"
    
    print("✅ Cálculo de score funcionou!")


def test_interview_flow():
    """Testa o fluxo completo da entrevista."""
    print("\n=== TESTE: FLUXO DA ENTREVISTA ===")
    session = create_test_session()
    
    # Primeira mensagem: início da entrevista
    response = handle_interview(session, "quero atualizar meu score")
    print(f"Resposta 1: {response.message[:100]}...")
    assert "renda mensal" in response.message.lower()
    
    # Responde com a renda
    response = handle_interview(session, "R$ 5.000,00")
    print(f"Resposta 2: {response.message[:100]}...")
    assert "vínculo" in response.message.lower() or "opções" in response.message.lower()
    
    # Responde com o tipo de emprego
    response = handle_interview(session, "CLT")
    print(f"Resposta 3: {response.message[:100]}...")
    assert "despesas" in response.message.lower()
    
    # Responde com as despesas
    response = handle_interview(session, "R$ 1.500,00")
    print(f"Resposta 4: {response.message[:100]}...")
    assert "dependentes" in response.message.lower()
    
    # Responde com dependentes
    response = handle_interview(session, "2")
    print(f"Resposta 5: {response.message[:100]}...")
    assert "dívidas" in response.message.lower() or "dividas" in response.message.lower()
    
    # Responde com dívidas
    response = handle_interview(session, "não")
    print(f"Resposta 6: {response.message[:100]}...")
    assert session._interview_state.completed
    assert session._interview_state.final_score is not None
    
    print("✅ Fluxo da entrevista funcionou!")


def test_csv_update():
    """Testa a atualização do CSV."""
    print("\n=== TESTE: ATUALIZAÇÃO NO CSV ===")
    
    # Lê o score inicial
    row = _get_client_row("45573022890")
    initial_score = int(row.get("score", 0))
    print(f"Score inicial: {initial_score}")
    
    # Atualiza o score
    new_score = 900
    ok = _update_client_score("45573022890", new_score)
    assert ok, "Falha ao atualizar score"
    
    # Verifica a atualização
    row = _get_client_row("45573022890")
    updated_score = int(row.get("score", 0))
    print(f"Score atualizado: {updated_score}")
    assert updated_score == new_score, f"Esperava {new_score}, obteve {updated_score}"
    
    # Restaura o score original
    _update_client_score("45573022890", initial_score)
    
    print("✅ Atualização no CSV funcionou!")


if __name__ == "__main__":
    test_parse_br_number()
    test_calculate_score()
    test_interview_flow()
    test_csv_update()
    print("\n🎉 Todos os testes passaram!")