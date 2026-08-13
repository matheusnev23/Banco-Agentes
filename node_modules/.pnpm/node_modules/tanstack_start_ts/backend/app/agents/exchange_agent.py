"""Agente de câmbio (cotação de moedas) usando AwesomeAPI."""

import json
import re
import unicodedata
from datetime import datetime
from urllib import request as url_request

from app.models.session import Session
from app.schemas.chat import ChatResponse
from app.schemas.exchange import ExchangeRate
from app.services.llm import llm_response
from app.utils import to_camel_dict

# URL base da AwesomeAPI
AWESOME_API_BASE = "https://economia.awesomeapi.com.br/json/last/"

# Mapeamento de moedas suportadas
SUPPORTED_CURRENCIES = {
    "USD": ("Dólar Americano", "USDBRL"),
    "EUR": ("Euro", "EURBRL"),
    "BTC": ("Bitcoin", "BTCBRL"),
    "GBP": ("Libra Esterlina", "GBPBRL"),
    "ARS": ("Peso Argentino", "ARSBRL"),
    "JPY": ("Iene Japonês", "JPYBRL"),
}

# Mapeamento por nome/variantes para detecção
CURRENCY_ALIASES = {
    "usd": "USD", "dolar": "USD", "dólar": "USD", "dollar": "USD",
    "real": "BRL", "reais": "BRL", "brl": "BRL",
    "eur": "EUR", "euro": "EUR",
    "btc": "BTC", "bitcoin": "BTC",
    "gbp": "GBP", "libra": "GBP", "libra esterlina": "GBP",
    "ars": "ARS", "peso": "ARS", "peso argentino": "ARS",
    "jpy": "JPY", "iene": "JPY", "iene japonês": "JPY",
}


def _normalize(text: str) -> str:
    """Normaliza texto: minúsculas e sem acentos."""
    text = unicodedata.normalize("NFD", text.lower())
    return re.sub(r"[\u0300-\u036f]", "", text)


def _log_agent(message: str) -> None:
    """Imprime no console qual agente está atendendo."""
    print(f"[AGENTE CAMBIO] {message}")


def _build_response(session_id: str, message: str, status: str, authenticated: bool, metadata: dict) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        message=message,
        status=status,
        authenticated=authenticated,
        metadata=metadata,
    )


def _fetch_rate(currency_pair: str) -> dict | None:
    """Busca a cotação atual na AwesomeAPI."""
    try:
        # Converte "USDBRL" para "USD-BRL" para a API
        if len(currency_pair) == 6:
            pair = f"{currency_pair[0:3]}-{currency_pair[3:6]}"
        else:
            pair = currency_pair
        url = f"{AWESOME_API_BASE}{pair}"
        req = url_request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with url_request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # A resposta vem como {"USDBRL": {...}}
        key = list(data.keys())[0]
        return data[key]
    except Exception as exc:
        print(f"[CAMBIAL ERROR] {type(exc).__name__}: {exc}")
        return None


def _get_rates() -> dict[str, ExchangeRate]:
    """Busca todas as cotações suportadas de uma vez."""
    # Monta o par de moedas: USD-BRL,EUR-BRL,BTC-BRL,...
    pairs = ",".join(
        f"{code[0:3]}-BRL" if len(SUPPORTED_CURRENCIES[code][1]) <= 6 else f"{code[0:3]}-BRL"
        for code in SUPPORTED_CURRENCIES
    ).replace("BTC-BRL", "BTC-BRL").replace("USD-BRL", "USD-BRL").replace("EUR-BRL", "EUR-BRL")

    # A AwesomeAPI aceita múltiplas cotações separadas por vírgula
    try:
        url = f"{AWESOME_API_BASE}{pairs}"
        req = url_request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with url_request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        rates: dict[str, ExchangeRate] = {}
        for code, (name, pair) in SUPPORTED_CURRENCIES.items():
            if code in data:
                item = data[code]
                rates[code] = ExchangeRate(
                    base=item.get("code", code),
                    quote=item.get("codein", "BRL"),
                    rate=float(item.get("bid", 0)),
                    variation=float(item.get("pctChange", 0)),
                    updated_at=item.get("create_date", datetime.now().isoformat()),
                )
        return rates
    except Exception as exc:
        print(f"[CAMBIAL ERROR] {type(exc).__name__}: {exc}")
        return {}


def _get_single_rate(base: str) -> ExchangeRate | None:
    """Busca a cotação de uma moeda específica."""
    if base not in SUPPORTED_CURRENCIES:
        return None
    _, pair = SUPPORTED_CURRENCIES[base]
    data = _fetch_rate(pair)
    if not data:
        return None
    return ExchangeRate(
        base=data.get("code", base),
        quote=data.get("codein", "BRL"),
        rate=float(data.get("bid", 0)),
        variation=float(data.get("pctChange", 0)),
        updated_at=data.get("create_date", datetime.now().isoformat()),
    )


def _parse_br_number(text: str) -> float | None:
    """Converte um número em formato brasileiro para float."""
    text = text.strip().replace("R$", "").replace("$", "").strip()
    if not text:
        return None

    # Remove sufixo mil/m
    text_lower = text.lower()
    if text_lower.endswith("mil") or text_lower.endswith("m"):
        num = text[:-3].strip() if text_lower.endswith("mil") else text[:-1].strip()
        v = _parse_br_number(num)
        return v * 1000 if v else None

    if text_lower.endswith("k"):
        num = text[:-1].strip()
        v = _parse_br_number(num)
        return v * 1000 if v else None

    if "," in text:
        cleaned = text.replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None

    if "." in text:
        parts = text.split(".")
        if len(parts) == 2 and len(parts[1]) <= 2:
            try:
                return float(text)
            except ValueError:
                return None
        cleaned = text.replace(".", "")
        try:
            return float(cleaned)
        except ValueError:
            return None

    try:
        return float(text)
    except ValueError:
        return None


def _detect_currency(message: str) -> str | None:
    """Detecta a moeda mencionada na mensagem."""
    text = _normalize(message)
    for alias, code in CURRENCY_ALIASES.items():
        if alias in text:
            if code != "BRL":
                return code
    # Verifica códigos diretos
    for code in SUPPORTED_CURRENCIES:
        if code.lower() in text:
            return code
    return None


def _detect_quantity(message: str) -> float | None:
    """Detecta uma quantidade numérica na mensagem."""
    import re

    # Primeiro verifica padrões com "mil" (ex: "1.5 mil", "2 mil", "1,5 mil")
    mil_match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*mil\b", message.lower())
    if mil_match:
        val = _parse_br_number(mil_match.group(1))
        return val * 1000 if val else None

    # Verifica padrões com "k" (ex: "10k", "2.5k")
    k_match = re.search(r"\b(\d+(?:[.,]\d+)?)k\b", message.lower())
    if k_match:
        val = _parse_br_number(k_match.group(1))
        return val * 1000 if val else None

    # Tenta parser direto
    direct = _parse_br_number(message)
    if direct is not None:
        return direct

    # Tenta extrair número de frases como "quanto é 100 dólares", "250 euros"
    patterns = [
        r"\b(\d+(?:[.,]\d+)?)\s*(?:dólares|dollars|euros|reais|usd|eur|btc|pesos|iene|libra)\b",
    ]
    text_lower = message.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            val = _parse_br_number(match.group(1))
            if val is not None:
                return val

    # Tenta encontrar qualquer número na mensagem
    match = re.search(r"\b(\d+(?:[.,]\d+)?)\b", message)
    if match:
        return _parse_br_number(match.group(0))
    return None


def _format_currency(value: float, currency: str = "BRL") -> str:
    """Formata valor monetário."""
    if currency == "BTC":
        return f"₿ {value:,.4f}"
    # Formato brasileiro: 1.000,00
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _detect_all_currencies(message: str) -> list[str]:
    """Detecta TODAS as moedas mencionadas na mensagem (ex: 20 euros e 100 dólares)."""
    text = _normalize(message)
    found: list[str] = []
    for alias, code in CURRENCY_ALIASES.items():
        if code != "BRL" and alias in text and code not in found:
            found.append(code)
    # Verifica códigos diretos
    for code in SUPPORTED_CURRENCIES:
        if code.lower() in text and code not in found:
            found.append(code)
    return found


def _detect_all_quantities(message: str) -> list[tuple[str, float]]:
    """Detecta moeda + quantidade para cada moeda mencionada.
    
    Ex: "20 euros e 100 dólares" -> [("EUR", 20.0), ("USD", 100.0)]
    """
    import re
    found: list[tuple[str, float]] = []
    text_lower = message.lower()
    
    # Padrão: "NOME_MOEDA QUANTIDADE" ou "QUANTIDADE NOME_MOEDA"
    for alias, code in CURRENCY_ALIASES.items():
        if code == "BRL":
            continue
        
        # Cria variantes com plural: "euro" -> "euros", "dolar" -> "dolares", "dólar" -> "dólares"
        alias_variants = [alias]
        if alias == "euro":
            alias_variants.append("euros")
        elif alias == "dolar":
            alias_variants.append("dolares")
        elif alias == "dólar":
            alias_variants.append("dólares")
        elif alias == "libra":
            alias_variants.append("libras")
        elif alias == "peso":
            alias_variants.append("pesos")
        elif alias == "iene":
            alias_variants.append("ienes")
        elif alias == "bitcoin":
            alias_variants.append("bitcoins")
        elif alias == "real":
            alias_variants.append("reais")
        elif alias.endswith("o"):
            alias_variants.append(alias + "s")
        elif alias.endswith("r"):
            alias_variants.append(alias + "es")
        elif alias.endswith("a"):
            alias_variants.append(alias + "s")
        elif alias.endswith("e"):
            alias_variants.append(alias + "s")
        
        # Padrões: "20 euros", "100 dólares", "20 EUR", "30 dolares", "5 mil euros"
        for variant in alias_variants:
            patterns = [
                rf"\b(\d+(?:[.,]\d+)?)\s*(?:mil\s+)?{re.escape(variant)}\b",
                rf"\b{re.escape(variant)}\s*(\d+(?:[.,]\d+)?)\b",
            ]
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    val = _parse_br_number(match.group(1))
                    if val is not None:
                        found.append((code, val))
                        break
            if found and found[-1][0] == code:
                break
    
    return found


def handle_exchange(session: Session, message: str) -> ChatResponse:
    """Lida com solicitações de câmbio/cotação de moedas."""
    _log_agent(f"ATENDENDO — sessão: {session.id} | mensagem: {message[:80]}")

    authenticated = session.client is not None

    # Detecta TODAS as moedas na mensagem
    currencies = _detect_all_currencies(message)
    currency_quantities = _detect_all_quantities(message)

    # Se detectou múltiplas moedas com quantidades, calcula conversão combinada
    if len(currency_quantities) >= 2:
        total_brl = 0.0
        rates_info: list[dict] = []
        all_ok = True
        
        for code, qty in currency_quantities:
            rate = _get_single_rate(code)
            if not rate:
                all_ok = False
                break
            converted = qty * rate.rate
            total_brl += converted
            rates_info.append({
                "base": rate.base,
                "quantity": qty,
                "rate": rate.rate,
                "converted": converted,
                "variation": rate.variation,
            })
        
        if all_ok:
            # Monta resposta com valores REAIS da API - NÃO deixa LLM inventar
            msg_lines = [f"💱 Conversão para Reais:\n"]
            for info in rates_info:
                msg_lines.append(
                    f"💰 {info['quantity']:,.2f} {info['base']} = {_format_currency(info['converted'])} "
                    f"(cotação: 1 {info['base']} = {_format_currency(info['rate'])})"
                )
            msg_lines.append(f"\n🧮 Total: {_format_currency(total_brl)}\n")
            msg_lines.append("Precisa de mais alguma coisa?")
            msg = "\n".join(msg_lines)
            session.add_message("assistant", msg)
            return _build_response(session.id, msg, "authenticated" if authenticated else "unauthenticated", authenticated, {"agent": "exchange"})

    # Detecta moedas simples
    currency = currencies[0] if currencies else None
    quantity_pair = currency_quantities[0] if currency_quantities else None

    # Se não detectou moeda, pergunta qual moeda quer consultar
    if not currency:
        system_prompt = (
            "Você é o agente de câmbio do Banco Ágil. "
            "O cliente quer ver cotações de moedas. "
            "Pergunte de forma natural qual moeda ele quer consultar. "
            "Liste as opções disponíveis: Dólar Americano (USD), Euro (EUR), "
            "Bitcoin (BTC), Libra Esterlina (GBP), Peso Argentino (ARS), Iene Japonês (JPY)."
        )
        chat_messages = [{"role": m["role"], "content": m["content"]} for m in session.history]
        llm_text = llm_response(chat_messages, system_prompt)

        if llm_text:
            session.add_message("assistant", llm_text)
            return _build_response(
                session.id,
                llm_text,
                "authenticated" if authenticated else "unauthenticated",
                authenticated,
                {"agent": "exchange"},
            )

        msg = (
            "Posso consultar cotações de moedas para você!\n\n"
            "Quais moedas deseja ver?\n"
            "- 🇺🇸 Dólar Americano (USD)\n"
            "- 🇪🇺 Euro (EUR)\n"
            "- ₿ Bitcoin (BTC)\n"
            "- 🇬🇧 Libra Esterlina (GBP)\n"
            "- 🇦🇷 Peso Argentino (ARS)\n"
            "- 🇯🇵 Iene Japonês (JPY)"
        )
        session.add_message("assistant", msg)
        return _build_response(session.id, msg, "authenticated" if authenticated else "unauthenticated", authenticated, {"agent": "exchange"})

    # Com moeda e quantidade (ex: "quanto é 100 dólares em reais")
    if currency and quantity_pair and quantity_pair[0] == currency:
        qty = quantity_pair[1]
        rate = _get_single_rate(currency)
        if not rate:
            msg = f"Não consegui obter a cotação de {currency} no momento. Tente novamente em instantes."
            session.add_message("assistant", msg)
            return _build_response(session.id, msg, "authenticated" if authenticated else "unauthenticated", authenticated, {"agent": "exchange"})

        # Calcula conversão - valores REAIS da API
        converted = qty * rate.rate

        msg = (
            f"💱 Conversão de {qty:,.2f} {rate.base} para Reais:\n\n"
            f"💰 1 {rate.base} = {_format_currency(rate.rate)}\n"
            f"🔢 {qty:,.2f} {rate.base} = {_format_currency(converted)}\n"
            f"📈 Variação: {rate.variation:+.2f}%\n\n"
            "Precisa de mais alguma coisa?"
        )
        session.add_message("assistant", msg)
        return _build_response(
            session.id,
            msg,
            "authenticated" if authenticated else "unauthenticated",
            authenticated,
            {"agent": "exchange", "widget": {"kind": "exchange_rate", "exchangeRate": to_camel_dict(rate)}},
        )

    # Só moeda (ex: "cotação do dólar")
    if currency:
        rate = _get_single_rate(currency)
        if not rate:
            msg = f"Não consegui obter a cotação de {currency} no momento. Tente novamente em instantes."
            session.add_message("assistant", msg)
            return _build_response(session.id, msg, "authenticated" if authenticated else "unauthenticated", authenticated, {"agent": "exchange"})

        msg = (
            f"💱 Cotação atual de {rate.base}:\n\n"
            f"💰 1 {rate.base} = {_format_currency(rate.rate)}\n"
            f"📈 Variação: {rate.variation:+.2f}%\n\n"
            "Quer converter algum valor?"
        )
        session.add_message("assistant", msg)
        return _build_response(
            session.id,
            msg,
            "authenticated" if authenticated else "unauthenticated",
            authenticated,
            {"agent": "exchange", "widget": {"kind": "exchange_rate", "exchangeRate": to_camel_dict(rate)}},
        )

    # Fallback
    msg = "Não entendi. Poderia me dizer qual moeda deseja consultar?"
    session.add_message("assistant", msg)
    return _build_response(session.id, msg, "authenticated" if authenticated else "unauthenticated", authenticated, {"agent": "exchange"})
