"""Testes rápidos para o agente de crédito."""

import csv
import sys
from pathlib import Path

# Adiciona o diretório backend ao path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.models.session import session_store
from app.schemas.auth import Client
from app.services.credit_service import (
    request_credit_increase,
    request_credit_decrease,
    get_credit_limit,
)
from app.services.credit_request_service import register_credit_request


def reset_client(cpf: str, total: float, usado: float):
    """Restaura o cliente no CSV para um estado conhecido."""
    import app.services.client_db as client_db
    from app.services.client_db import update_client_limits
    update_client_limits(cpf, total, usado)
    # Invalida cache para garantir dados atualizados
    client_db._cache = None


def update_client_score(cpf: str, score: int):
    """Atualiza o score de um cliente no CSV."""
    import app.services.client_db as client_db
    csv_path = Path(__file__).resolve().parent / "data" / "clientes.csv"
    rows = []
    fieldnames = None
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["cpf"].strip() == cpf:
                row["score"] = str(score)
            rows.append(row)
    if fieldnames:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    client_db._cache = None


def create_test_session(cpf: str = "45573022890", limite_total: float = 2500.0, limite_usado: float = 0.0):
    """Cria uma sessão de teste com cliente autenticado."""
    session = session_store.create()
    limite_disponivel = limite_total - limite_usado
    session.client = Client(
        id="test_client",
        name="Matheus Neves",
        masked_document="***.***.***-90",
        limite_total=limite_total,
        limite_disponivel=limite_disponivel,
    )
    session.client_cpf = cpf
    session.status = "authenticated"
    return session


def test_increase():
    """Testa aumento de limite."""
    print("\n=== TESTE: AUMENTO DE LIMITE ===")
    reset_client("45573022890", 2500.0, 0.0)
    # Garante score >= 800 para aprovação
    update_client_score("45573022890", 850)
    session = create_test_session()
    result = request_credit_increase(session.id, 5000.0)
    print(f"Status: {result.status}")
    print(f"Novo total: {result.new_total}")
    print(f"Nova disponibilidade: {result.new_available}")
    assert result.status == "approved", f"Esperava approved, obteve {result.status}"
    assert result.new_total == 5000.0
    print("✅ Aumento de limite funcionou!")


def test_decrease_below_used():
    """Testa diminuição de limite abaixo do utilizado (deve ser rejeitado)."""
    print("\n=== TESTE: DIMINUIÇÃO ABAIXO DO UTILIZADO ===")
    reset_client("52998224725", 12000.0, 3000.0)
    session = create_test_session(cpf="52998224725", limite_total=12000.0, limite_usado=3000.0)
    result = request_credit_decrease(session.id, 2000.0)  # Abaixo do utilizado (3000)
    print(f"Status: {result.status}")
    print(f"Mensagem: {result.message}")
    assert result.status == "rejected", f"Esperava rejected, obteve {result.status}"
    print("✅ Diminuição abaixo do utilizado foi rejeitada!")


def test_decrease_valid():
    """Testa diminuição de limite válida."""
    print("\n=== TESTE: DIMINUIÇÃO VÁLIDA ===")
    reset_client("52998224725", 12000.0, 3000.0)
    session = create_test_session(cpf="52998224725", limite_total=12000.0, limite_usado=3000.0)
    result = request_credit_decrease(session.id, 8000.0)  # Acima do utilizado (3000)
    print(f"Status: {result.status}")
    print(f"Novo total: {result.new_total}")
    print(f"Nova disponibilidade: {result.new_available}")
    assert result.status == "approved", f"Esperava approved, obteve {result.status}"
    assert result.new_total == 8000.0
    assert result.new_available == 5000.0  # 8000 - 3000 utilizado
    print("✅ Diminuição válida funcionou!")


def test_decrease_equal_or_higher():
    """Testa diminuição com valor igual ou maior que o atual (deve ser rejeitado)."""
    print("\n=== TESTE: DIMINUIÇÃO COM VALOR IGUAL/MAIOR ===")
    reset_client("52998224725", 12000.0, 3000.0)
    session = create_test_session(cpf="52998224725", limite_total=12000.0, limite_usado=3000.0)
    result = request_credit_decrease(session.id, 12000.0)  # Igual ao atual
    print(f"Status: {result.status}")
    print(f"Mensagem: {result.message}")
    assert result.status == "rejected", f"Esperava rejected, obteve {result.status}"
    print("✅ Diminuição com valor igual foi rejeitada!")


def test_increase_with_low_score():
    """Testa aumento de limite com score abaixo de 800 (deve ser rejeitado e oferecer entrevista)."""
    print("\n=== TESTE: AUMENTO COM SCORE BAIXO ===")
    reset_client("52998224725", 12000.0, 3000.0)
    session = create_test_session(cpf="52998224725", limite_total=12000.0, limite_usado=3000.0)
    result = request_credit_increase(session.id, 15000.0)
    print(f"Status: {result.status}")
    print(f"Mensagem: {result.message}")
    assert result.status == "rejected", f"Esperava rejected, obteve {result.status}"
    assert "score" in result.message.lower(), "Mensagem deve mencionar o score"
    assert "entrevista" in result.message.lower(), "Mensagem deve oferecer entrevista"
    print("✅ Aumento com score baixo foi rejeitado e oferece entrevista!")


def test_csv_registration():
    """Testa registro no CSV."""
    print("\n=== TESTE: REGISTRO NO CSV ===")
    ok = register_credit_request(
        cpf_cliente="45573022890",
        limite_atual=2500.0,
        novo_limite_solicitado=5000.0,
        status_pedido="aprovado",
    )
    assert ok, "Falha ao registrar no CSV"
    print("✅ Registro no CSV funcionou!")


if __name__ == "__main__":
    test_increase()
    test_decrease_below_used()
    test_decrease_valid()
    test_decrease_equal_or_higher()
    test_increase_with_low_score()
    test_csv_registration()
    print("\n🎉 Todos os testes passaram!")
