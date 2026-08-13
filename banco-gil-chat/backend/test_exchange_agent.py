"""Testes para o agente de câmbio (cotação de moedas)."""

import sys
import os
from pathlib import Path

# Adiciona o diretório backend ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.models.session import session_store, Session
from app.agents.exchange_agent import (
    handle_exchange,
    _detect_currency,
    _detect_quantity,
    _parse_br_number,
    _format_currency,
    SUPPORTED_CURRENCIES,
)


def create_test_session():
    """Cria uma sessão de teste com cliente autenticado."""
    from app.schemas.auth import Client

    session = session_store.get_or_create("test_exchange")
    session.client = Client(
        id="client_test_001",
        name="Teste Usuario",
        document="12345678909",
        masked_document="***.456.789-**",
        email="teste@test.com",
        score=850,
        limite_disponivel=5000.0,
        limite_total=10000.0,
    )
    session.client_cpf = "12345678909"
    session.status = "authenticated"
    return session


def test_detect_currency():
    """Testa detecção de moedas na mensagem."""
    print("\n=== TESTE: DETECÇÃO DE MOEDAS ===")

    tests = [
        ("cotação do dólar", "USD"),
        ("quanto é o euro hoje", "EUR"),
        ("preço do bitcoin", "BTC"),
        ("cotação da libra", "GBP"),
        ("peso argentino", "ARS"),
        ("iene japonês", "JPY"),
        ("usd para brl", "USD"),
    ]

    for msg, expected in tests:
        result = _detect_currency(msg)
        assert result == expected, f"Falha: '{msg}' -> esperado {expected}, got {result}"
        print(f"✅ '{msg}' -> {result}")


def test_detect_quantity():
    """Testa detecção de quantidade monetária."""
    print("\n=== TESTE: DETECÇÃO DE QUANTIDADE ===")

    tests = [
        ("quanto é 100 dólares em reais", 100.0),
        ("quero converter 250 euros", 250.0),
        ("1.5 mil reais", 1500.0),
        ("10k", 10000.0),
        ("R$ 5.000,50", 5000.5),
    ]

    for msg, expected in tests:
        result = _detect_quantity(msg)
        assert result == expected, f"Falha: '{msg}' -> esperado {expected}, got {result}"
        print(f"✅ '{msg}' -> {result}")


def test_parse_br_number():
    """Testa conversão de formatos brasileiros."""
    print("\n=== TESTE: PARSE BR NUMBER ===")

    tests = [
        ("2000", 2000.0),
        ("2.000", 2000.0),
        ("2.000,50", 2000.5),
        ("2,5", 2.5),
        ("R$ 2.000", 2000.0),
        ("15k", 15000.0),
        ("15K", 15000.0),
        ("1.5 mil", 1500.0),
    ]

    for val, expected in tests:
        result = _parse_br_number(val)
        assert result == expected, f"Falha: '{val}' -> esperado {expected}, got {result}"
        print(f"✅ '{val}' -> {result}")


def test_format_currency():
    """Testa formatação de moeda."""
    print("\n=== TESTE: FORMATAÇÃO ===")

    assert "R$ 1.000,00" in _format_currency(1000.0)
    assert "R$ 5.727,60" in _format_currency(5727.6)
    print("✅ Formatação BRL correta")

    btc = _format_currency(0.5, "BTC")
    assert "₿" in btc
    print(f"✅ Formatação BTC correta: {btc}")


def test_exchange_flow_question():
    """Testa fluxo quando cliente pede cotação sem especificar moeda."""
    print("\n=== TESTE: FLUXO SEM MOEDA ESPECÍFICA ===")
    session = create_test_session()

    response = handle_exchange(session, "quero ver cotações de moedas")
    print(f"Resposta: {response.message[:120]}...")
    assert response.metadata.get("agent") == "exchange"
    print("✅ Agente exchange respondeu")


def test_exchange_flow_specific():
    """Testa fluxo quando cliente pede cotação de moeda específica."""
    print("\n=== TESTE: FLUXO COM MOEDA ESPECÍFICA ===")
    session = create_test_session()

    response = handle_exchange(session, "cotação do dólar")
    print(f"Resposta: {response.message[:120]}...")
    assert response.metadata.get("agent") == "exchange"
    print("✅ Agente exchange respondeu para dólar")


def test_exchange_flow_conversion():
    """Testa fluxo com conversão de valores."""
    print("\n=== TESTE: FLUXO COM CONVERSÃO ===")
    session = create_test_session()

    response = handle_exchange(session, "quanto é 100 dólares em reais")
    print(f"Resposta: {response.message[:150]}...")
    assert response.metadata.get("agent") == "exchange"
    print("✅ Agente exchange respondeu conversão")


def test_supported_currencies():
    """Testa se as moedas suportadas estão corretas."""
    print("\n=== TESTE: MOEDAS SUPORTADAS ===")
    assert "USD" in SUPPORTED_CURRENCIES
    assert "EUR" in SUPPORTED_CURRENCIES
    assert "BTC" in SUPPORTED_CURRENCIES
    assert "GBP" in SUPPORTED_CURRENCIES
    assert "ARS" in SUPPORTED_CURRENCIES
    assert "JPY" in SUPPORTED_CURRENCIES
    print(f"✅ {len(SUPPORTED_CURRENCIES)} moedas suportadas")