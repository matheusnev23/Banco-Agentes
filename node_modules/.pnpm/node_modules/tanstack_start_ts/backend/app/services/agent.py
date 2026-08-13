"""Agente de triagem - fluxo de autenticação e redirecionamento.

Fluxo do agente de triagem:
1. Saudação inicial.
2. Coleta do CPF.
3. Coleta da data de nascimento.
4. Validação dos dados contra a base (clientes.csv) para autenticação.
5. Se autenticado:
   - Identifica o assunto da solicitação.
   - Redireciona para o agente adequado (silenciosamente, sem avisar o cliente).
6. Se não autenticado:
   - Informa a falha. Permite até 2 novas tentativas.
   - Após a 3ª falha consecutiva, encerra o atendimento de forma agradável.

Mensagens de console de controle são impressas para acompanhar o fluxo.
"""

import json
import re
import unicodedata
from urllib import request as url_request
from urllib.error import URLError

from openai import OpenAI

from app.config import settings
from app.models.session import Session
from app.schemas.auth import Client
from app.schemas.chat import ChatResponse, ServiceStatus
from app.schemas.credit import CreditLimit
from app.schemas.exchange import ExchangeRate
from app.schemas.interview import InterviewQuestion
from app.agents.credit_agent import handle_message as handle_credit_message
from app.agents.credit_interview_agent import handle_interview
from app.agents.exchange_agent import handle_exchange
from app.services.client_db import authenticate as authenticate_client
from app.services.prompt_service import build_triage_prompt
from app.utils import to_camel_dict

MAX_AUTH_ATTEMPTS = 3

MOCK_EXCHANGE_RATES: list[ExchangeRate] = [
    ExchangeRate(base="USD", quote="BRL", rate=5.42, variation=0.42),
    ExchangeRate(base="EUR", quote="BRL", rate=5.89, variation=-0.18),
    ExchangeRate(base="GBP", quote="BRL", rate=6.94, variation=0.11),
    ExchangeRate(base="ARS", quote="BRL", rate=0.0061, variation=-0.9),
]

MOCK_INTERVIEW_QUESTIONS: list[InterviewQuestion] = [
    InterviewQuestion(id="income", label="Qual é a sua renda mensal?", kind="currency", placeholder="0,00"),
    InterviewQuestion(
        id="employment",
        label="Qual é o seu tipo de vínculo?",
        kind="choice",
        options=["CLT", "Autônomo", "Empresário", "Servidor público", "Aposentado"],
    ),
    InterviewQuestion(id="expenses", label="Quanto somam suas despesas fixas?", kind="currency", placeholder="0,00"),
    InterviewQuestion(id="dependents", label="Quantos dependentes você possui?", kind="number", placeholder="0"),
    InterviewQuestion(
        id="debts",
        label="Você possui dívidas em aberto?",
        kind="choice",
        options=["Não possuo", "Sim, em negociação", "Sim, em atraso"],
    ),
]

MOCK_SERVICE_ERROR = {
    "title": "Não foi possível concluir sua solicitação.",
    "description": "Estamos enfrentando uma instabilidade temporária. Tente novamente em alguns instantes.",
    "retryable": True,
}

# --- Utilitários ---

Intent = str  # "credit_limit" | "credit_increase" | "credit_decrease" | "exchange" | "interview" | "score" | "error" | "closing" | "fallback"


def _normalize(value: str) -> str:
    """Remove acentos e converte para minúsculas."""
    text = unicodedata.normalize("NFD", value.lower())
    return re.sub(r"[\u0300-\u036f]", "", text)


def detect_intent(message: str) -> Intent:
    """Detecta a intenção da mensagem do usuário (fallback por palavras-chave)."""
    # Se a mensagem parece ser apenas dados de autenticação (CPF, data, números), não classifica
    normalized_msg = message.strip()
    is_auth_data = bool(re.match(r"^[\d\s\./\-]+$", normalized_msg)) and len(normalized_msg) < 30
    if is_auth_data:
        return "fallback"
    
    text = _normalize(message)
    
    # Evita classificar como erro mensagens que contêm apenas números ou datas
    if re.search(r"(erro|instabilidade|falha|indisponi)", text) and not is_auth_data:
        return "error"
    if re.search(r"(encerrar|finalizar|tchau|obrigad)", text):
        return "closing"
    # "Atualizar meu score" / "fazer entrevista" é intenção de entrevista
    if re.search(r"(atualizar meu score|atualizar score|fazer.*entrevista|iniciar.*entrevista|entrevista financeira|refazer.*entrevista)", text):
        return "interview"
    # Consulta de score
    if re.search(r"(ver meu score|consultar score|mostrar score|exibir score|meu score)", text):
        return "score"
    if re.search(r"(score|entrevista|financeir)", text) and not re.search(r"(ver|consultar|mostrar|exibir)", text):
        return "interview"
    
    # Câmbio - verifica ANTES de crédito para mensagens com moedas
    if re.search(r"(cotacao|dolar|dólar|euro|cambio|moeda|usd|eur|btc|bitcoin|libra|peso|iene)", text):
        return "exchange"
    
    # Aumento de limite - múltiplos padrões
    # Padrão: "preciso de X", "quero X", "desejo X" + número
    if re.search(r"(preciso|quero|desejo|solicito|pedir|solicitar)\s+(de\s+)?(um\s+)?(aumento\s+)?(de\s+)?(limite\s+)?(para\s+)?", text):
        # Verifica se tem número na mensagem
        if re.search(r"\d+", message):
            return "credit_increase"
    # Padrão: "aumentar limite para X"
    if re.search(r"(aumentar|elevar|aumento)\s+(limite\s+)?(para\s+)?", text) and re.search(r"\d+", message):
        return "credit_increase"
    # Padrão: "15 mil", "10k", "15k"
    if re.search(r"\b\d+\s*mil\b", text) or re.search(r"\b\d+[km]\b", text.lower()):
        return "credit_increase"
    # Palavras-chave de aumento (mesmo sem número)
    if re.search(r"(aumento|aumentar|elevar|novo limite|quer[oa]?[oa]? aumentar)", text):
        return "credit_increase"
    
    # Diminuição de limite
    if re.search(r"(diminuir|diminuicao|reduzir|reducao|baixar|menor limite)", text):
        return "credit_decrease"
    
    # Consulta de limite
    if re.search(r"(limite|credito|cartao|fatura)", text):
        return "credit_limit"
    
    return "fallback"


def select_rate(message: str) -> ExchangeRate:
    """Seleciona a cotação com base na moeda mencionada."""
    text = _normalize(message)
    if "euro" in text or "eur" in text:
        return MOCK_EXCHANGE_RATES[1]
    if "libra" in text or "gbp" in text:
        return MOCK_EXCHANGE_RATES[2]
    if "peso" in text or "ars" in text:
        return MOCK_EXCHANGE_RATES[3]
    return MOCK_EXCHANGE_RATES[0]


# --- Extração de informações do texto ---

_CPF_PATTERN = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")

# Mapeamento de meses por extenso (pt-BR) para número
_MONTHS_PT = {
    "janeiro": "01", "fevereiro": "02", "marco": "03", "março": "03",
    "abril": "04", "maio": "05", "junho": "06", "julho": "07",
    "agosto": "08", "setembro": "09", "outubro": "10",
    "novembro": "11", "dezembro": "12",
}

_DATE_PATTERNS = [
    re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b"),  # dd/mm/aaaa
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),  # aaaa-mm-dd
    re.compile(r"\b(\d{2})[./-](\d{2})[./-](\d{4})\b"),  # dd.mm.aaaa ou dd-mm-aaaa
    re.compile(r"\b(\d{2})\s+(\d{2})\s+(\d{4})\b"),  # dd mm aaaa (separado por espaço)
    re.compile(r"(?<!\d)(\d{8})(?!\d)"),  # ddmmaaaa (tudo junto)
    re.compile(r"\b(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4})\b", re.IGNORECASE),  # 23 de dezembro de 2003
    re.compile(r"\b(\d{1,2})\s+([a-zç]+)\s+(\d{4})\b", re.IGNORECASE),  # 23 dezembro 2003
]


def _extract_cpf(message: str) -> str | None:
    """Extrai um CPF (com ou sem pontuação) do texto da mensagem."""
    match = _CPF_PATTERN.search(message)
    if match:
        return re.sub(r"\D", "", match.group(0))
    return None


def _extract_birth_date(message: str) -> str | None:
    """Extrai uma data de nascimento do texto.

    Suporta formatos:
    - dd/mm/aaaa (15/03/1988)
    - aaaa-mm-dd (1988-03-15)
    - dd.mm.aaaa (15.03.1988)
    - dd-mm-aaaa (15-03-1988)
    - dd mm aaaa (15 03 1988)
    - ddmmaaaa (15031988)
    - dd de mês de aaaa (15 de março de 1988)
    - dd mês aaaa (15 março 1988)
    """
    for pattern in _DATE_PATTERNS:
        match = pattern.search(message)
        if match:
            groups = match.groups()
            if len(groups) == 1:
                # Formato ddmmaaaa (tudo junto): "23122003"
                raw = groups[0]
                if len(raw) == 8:
                    day = raw[0:2]
                    month = raw[2:4]
                    year = raw[4:8]
                    return f"{year}-{month}-{day}"
                continue
            if len(groups) == 3:
                a, b, c = groups
                # Se o mês é por extenso, converte para número
                if b and b.lower() in _MONTHS_PT:
                    b = _MONTHS_PT[b.lower()]
                if len(a) == 2:
                    return f"{c}-{b}-{a}"
                return f"{a}-{b}-{c}"
            if len(groups) == 2:
                # Formato "23 dez 2003" onde mês pode ser abreviado
                a, b = groups
                if b and b.lower() in _MONTHS_PT:
                    b = _MONTHS_PT[b.lower()]
                # Não temos o ano aqui, continua
                continue
    return None


# --- Integração com LLM (OpenRouter, Gemini ou OpenAI) ---

_client: OpenAI | None = None

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _get_client() -> OpenAI | None:
    """Retorna o cliente OpenAI (ou OpenRouter, que é compatível) se a chave estiver configurada."""
    global _client
    if settings.ai_provider == "openrouter" and settings.openrouter_api_key and _client is None:
        _client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
    elif settings.ai_provider == "openai" and settings.openai_api_key and _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def _has_llm() -> bool:
    """Retorna True se algum provedor de IA estiver configurado."""
    if settings.ai_provider == "gemini":
        return bool(settings.gemini_api_key)
    if settings.ai_provider == "openrouter":
        return bool(settings.openrouter_api_key)
    return bool(settings.openai_api_key)


def _gemini_response(messages: list[dict[str, str]], system_prompt: str | None = None) -> str | None:
    """Gera uma resposta usando o Google Gemini via API REST."""
    if not settings.gemini_api_key:
        return None
    try:
        contents = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        payload: dict = {"contents": contents}
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        payload["generationConfig"] = {"maxOutputTokens": 300}

        url = GEMINI_URL.format(model=settings.gemini_model)
        req = url_request.Request(
            f"{url}?key={settings.gemini_api_key}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with url_request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        candidates = data.get("candidates") or []
        if candidates:
            parts = candidates[0].get("content", {}).get("parts") or []
            if parts:
                return parts[0].get("text", "").strip() or None
        return None
    except Exception as exc:
        print(f"[GEMINI ERROR] {type(exc).__name__}: {exc}")
        return None


def _gemini_intent(message: str, history: list[dict[str, str]]) -> Intent | None:
    """Usa o Gemini para identificar a intenção do cliente."""
    if not settings.gemini_api_key:
        return None
    try:
        contents = []
        for m in history:
            role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        payload: dict = {
            "contents": contents,
            "systemInstruction": {
                "parts": [
                    {
                        "text": (
                            "Você é um classificador de intenções de um banco. "
                            "Analise a conversa do cliente e retorne APENAS um JSON no formato "
                            '{"intent": "credit_limit|credit_increase|credit_decrease|exchange|interview|error|closing|fallback"}. '
                            "Não escreva mais nada além do JSON."
                        )
                    }
                ]
            },
            "generationConfig": {"maxOutputTokens": 50, "temperature": 0},
        }

        url = GEMINI_URL.format(model=settings.gemini_model)
        req = url_request.Request(
            f"{url}?key={settings.gemini_api_key}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with url_request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        candidates = data.get("candidates") or []
        if candidates:
            parts = candidates[0].get("content", {}).get("parts") or []
            if parts:
                content = parts[0].get("text", "") or ""
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    intent = parsed.get("intent", "fallback")
                    valid = {"credit_limit", "credit_increase", "credit_decrease", "exchange", "interview", "score", "error", "closing", "fallback"}
                    return intent if intent in valid else "fallback"
        return None
    except Exception as exc:
        print(f"[GEMINI INTENT ERROR] {type(exc).__name__}: {exc}")
        return None


def _llm_response(messages: list[dict[str, str]], system_prompt: str | None = None) -> str | None:
    """Gera uma resposta usando o provedor de IA configurado (OpenRouter, Gemini ou OpenAI)."""
    if settings.ai_provider == "gemini":
        return _gemini_response(messages, system_prompt)

    client = _get_client()
    if client is None:
        return None
    try:
        model = (
            settings.openrouter_model
            if settings.ai_provider == "openrouter"
            else settings.openai_model
        )
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt or "Você é o assistente virtual do Banco Ágil."},
                *messages,
            ],
            max_tokens=300,
        )
        return completion.choices[0].message.content
    except Exception as exc:
        print(f"[LLM ERROR] {type(exc).__name__}: {exc}")
        return None


def _llm_intent(message: str, history: list[dict[str, str]]) -> Intent | None:
    """Usa a IA para identificar a intenção do cliente a partir da conversa."""
    if settings.ai_provider == "gemini":
        return _gemini_intent(message, history)

    client = _get_client()
    if client is None:
        return None
    try:
        model = (
            settings.openrouter_model
            if settings.ai_provider == "openrouter"
            else settings.openai_model
        )
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um classificador de intenções de um banco. "
                        "Analise a conversa do cliente e retorne APENAS um JSON no formato "
                        '{"intent": "credit_limit|credit_increase|credit_decrease|exchange|interview|score|error|closing|fallback"}. '
                        "Não escreva mais nada além do JSON."
                    ),
                },
                *history,
                {"role": "user", "content": message},
            ],
            max_tokens=50,
            temperature=0,
        )
        content = completion.choices[0].message.content or ""
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            intent = data.get("intent", "fallback")
            valid = {"credit_limit", "credit_increase", "credit_decrease", "exchange", "interview", "score", "error", "closing", "fallback"}
            return intent if intent in valid else "fallback"
        return None
    except Exception as exc:
        print(f"[LLM INTENT ERROR] {type(exc).__name__}: {exc}")
        return None


def build_response(session_id: str, message: str, status: ServiceStatus, authenticated: bool, metadata: dict) -> ChatResponse:
    """Monta a resposta padrão do chat."""
    return ChatResponse(
        session_id=session_id,
        message=message,
        status=status,
        authenticated=authenticated,
        metadata=metadata,
    )


def _to_client(record) -> Client:
    """Converte um ClientRecord num Client autenticado."""
    from app.routers.auth import _to_client as _auth_to_client
    return _auth_to_client(record)


def _client_credit_limit(client: Client | None) -> CreditLimit:
    """Retorna o limite de crédito do cliente autenticado."""
    if client is None:
        return CreditLimit(available=0, total=0)
    return CreditLimit(available=client.limite_disponivel, total=client.limite_total)


# --- Lógica principal do agente de triagem ---

def _log_agent(message: str) -> None:
    """Imprime no console qual agente está atendendo."""
    print(f"[AGENTE TRIAGEM] {message}")


def _is_service_intent(intent: str) -> bool:
    """Verifica se a intenção requer autenticação (serviços que precisam de login)."""
    service_intents = {
        "credit_limit",
        "credit_increase",
        "credit_decrease",
        "interview",
        "score",
    }
    return intent in service_intents


def _handle_pre_auth_conversation(session: Session, message: str) -> ChatResponse:
    """Gerencia a conversa ANTES da autenticação.
    
    Permite que o cliente tire dúvidas e converse livremente.
    Só solicita autenticação quando demonstrar interesse em um serviço.
    """
    # Detecta intenção da mensagem
    detected_intent = detect_intent(message)
    
    # Câmbio NÃO requer autenticação - redireciona diretamente
    if detected_intent == "exchange":
        print(f"[TRIAGEM] Cliente quer cotações de moedas. Redirecionando para agente de câmbio.")
        return handle_exchange(session, message)
    
    # Verifica se é uma intenção de serviço que requer autenticação
    if detected_intent != "fallback" and _is_service_intent(detected_intent):
        session.pending_intent = detected_intent
        print(f"[TRIAGEM] Cliente demonstrou interesse em: {detected_intent}. Solicitando autenticação.")
        
        # Marca que está aguardando autenticação
        session._authenticating = True
        
        # Resposta natural pedindo autenticação
        system_prompt = (
            "Você é o assistente virtual do Banco Ágil. "
            "O cliente demonstrou interesse em um serviço que requer autenticação. "
            "Peça o CPF e data de nascimento de forma natural e acolhedora. "
            "Explique que precisa desses dados para verificar sua identidade e liberar o serviço."
        )
        chat_messages = [{"role": m["role"], "content": m["content"]} for m in session.history]
        llm_text = _llm_response(chat_messages, system_prompt)
        
        if llm_text:
            session.add_message("assistant", llm_text)
            return build_response(
                session.id,
                llm_text,
                "authenticating",
                False,
                {"agent": "triage", "needs_auth": True},
            )
        
        # Fallback sem LLM
        msg = "Para ajudá-lo com isso, preciso verificar sua identidade. Por favor, informe seu CPF."
        session.add_message("assistant", msg)
        return build_response(
            session.id,
            msg,
            "authenticating",
            False,
            {"agent": "triage", "needs_auth": True},
        )
    
    # Se não é intenção de serviço, conversa livremente (fallback)
    system_prompt = (
        "Você é o assistente virtual do Banco Ágil. "
        "Converse naturalmente com o cliente, responda suas perguntas e tire suas dúvidas. "
        "Seja amigável, útil e profissional. "
        "NÃO peça dados de autenticação ainda - apenas converse. "
        "Se o cliente perguntar sobre serviços específicos (limite, score, entrevista), "
        "informe que você pode ajudá-lo e que precisará autenticá-lo primeiro."
    )
    chat_messages = [{"role": m["role"], "content": m["content"]} for m in session.history]
    llm_text = _llm_response(chat_messages, system_prompt)
    
    if llm_text:
        session.add_message("assistant", llm_text)
        return build_response(
            session.id,
            llm_text,
            "unauthenticated",
            False,
            {"agent": "triage"},
        )
    
    # Fallback sem LLM
    msg = "Olá! Como posso ajudá-lo hoje? Posso esclarecer dúvidas sobre nossos serviços."
    session.add_message("assistant", msg)
    return build_response(
        session.id,
        msg,
        "unauthenticated",
        False,
        {"agent": "triage"},
    )


def handle_message(session: Session, message: str) -> ChatResponse:
    """Processa uma mensagem do usuário no fluxo do agente de triagem.

    Fluxo:
    1. Converse livremente com o cliente (antes da autenticação).
    2. Quando o cliente demonstrar interesse em um serviço, solicite autenticação.
    3. Coleta do CPF e data de nascimento.
    4. Validação contra clientes.csv.
    5. Se autenticado: identifica o assunto e redireciona silenciosamente.
    6. Se não autenticado: informa falha, permite 2 novas tentativas, encerra após 3ª.
    """
    _log_agent(f"ATENDENDO — sessão: {session.id} | mensagem: {message[:80]}")
    # Adiciona a mensagem do usuário ao histórico
    session.add_message("user", message)

    # Se há um agente ativo (ex: entrevista em andamento), roteia direto para ele
    active_agent = getattr(session, "active_agent", None)
    if active_agent == "credit_interview":
        return handle_interview(session, message)

    authenticated = session.client is not None

    # --- Cliente autenticado: identifica o assunto e redireciona ---
    if authenticated:
        # Se há uma intenção pendente de antes da autenticação, preserva
        pending_intent = getattr(session, "pending_intent", None)
        
        intent = detect_intent(message) or _llm_intent(message, session.history) or "fallback"
        
        # Se a mensagem atual parece ser apenas dados de autenticação (curta, numérica)
        # e há uma intenção pendente, usa a intenção pendente
        if pending_intent and pending_intent not in ("error", "closing"):
            normalized_msg = message.strip()
            is_auth_data = bool(re.match(r"^[\d\s\./\-]+$", normalized_msg)) and len(normalized_msg) < 30
            if is_auth_data and intent == "fallback":
                intent = pending_intent
                print(f"[TRIAGEM] Usando intenção pendente: {intent}")
            else:
                session.pending_intent = intent
                print(f"[TRIAGEM] Assunto identificado: {intent}")
        else:
            session.pending_intent = intent
            print(f"[TRIAGEM] Assunto identificado: {intent}")
        
        # Limpa intenção pendente após usá-la
        if intent != "fallback":
            session.pending_intent = None

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

        if intent in ("credit_limit", "credit_increase", "credit_decrease"):
            return handle_credit_message(session, message, intent)

        if intent == "interview":
            return handle_interview(session, message)

        if intent == "score":
            return _handle_score_consult(session, message)

        if intent == "exchange":
            return handle_exchange(session, message)

        return _handle_authenticated_intent(session, intent, message)

    # --- Cliente NÃO autenticado: verifica se está em processo de autenticação ---
    if not authenticated:
        # Verifica se o cliente está no meio do processo de autenticação
        is_authenticating = getattr(session, "_authenticating", False)
        pending_intent = getattr(session, "pending_intent", None)
        
        # Se já está autenticando ou tem intenção pendente que requer auth, coleta dados
        if is_authenticating or (pending_intent and _is_service_intent(pending_intent)):
            cpf = _extract_cpf(message)
            birth = _extract_birth_date(message)

            # Se ainda não tem CPF, pede CPF PRIMEIRO.
            # A data de nascimento enviada antes do CPF é IGNORADA para
            # garantir a ordem correta de coleta (CPF → data de nascimento).
            if not session._partial_cpf:
                if cpf:
                    session._partial_cpf = cpf
                else:
                    msg = "Para começar, me informe seu CPF, por favor."
                    session.add_message("assistant", msg)
                    return build_response(
                        session.id,
                        msg,
                        "authenticating",
                        False,
                        {"agent": "triage"},
                    )

            # Tem CPF mas não tem data de nascimento, pede
            if not session._partial_birth:
                if birth:
                    session._partial_birth = birth
                else:
                    msg = "Agora me informe sua data de nascimento."
                    session.add_message("assistant", msg)
                    return build_response(
                        session.id,
                        msg,
                        "authenticating",
                        False,
                        {"agent": "triage"},
                    )

            effective_cpf = session._partial_cpf
            effective_birth = session._partial_birth

            # Tem CPF e data: valida contra a base
            record = authenticate_client(effective_cpf, effective_birth)
            if record:
                session.auth_attempts = 0
                session.client = _to_client(record)
                session.client_cpf = record.cpf
                session.status = "authenticated"
                session._authenticating = False
                authenticated = True
                print(f"[TRIAGEM] Cliente autenticado: {record.nome} (CPF {record.cpf})")

                # Se havia intenção pendente, redireciona diretamente sem perguntar "Como posso ajudar?"
                pending_intent = getattr(session, "pending_intent", None)
                print(f"[TRIAGEM] pending_intent após auth: {pending_intent}")
                if pending_intent and pending_intent not in ("error", "closing"):
                    print(f"[TRIAGEM] Após autenticação, redirecionando para: {pending_intent}")
                    # Limpa a intenção pendente para não reprocessar
                    session.pending_intent = None
                    
                    # Resposta padrão de autenticação sem LLM
                    msg = f"Tudo certo, {record.nome.split(' ')[0]}. Como posso ajudar?"
                    session.add_message("assistant", msg)
                    
                    if pending_intent in ("credit_limit", "credit_increase", "credit_decrease"):
                        return handle_credit_message(session, "", pending_intent)
                    elif pending_intent == "interview":
                        return handle_interview(session, "")
                    elif pending_intent == "exchange":
                        return handle_exchange(session, "")
                    else:
                        # Para outros, usa o handler genérico
                        return _handle_authenticated_intent(session, pending_intent, "")

                # Se não há intenção pendente, pergunta como pode ajudar (sem LLM)
                msg = f"Tudo certo, {record.nome.split(' ')[0]}. Como posso ajudar?"
                session.add_message("assistant", msg)
                return build_response(
                    session.id,
                    msg,
                    "authenticated",
                    True,
                    {"agent": "triage", "client": to_camel_dict(session.client)},
                )
            else:
                session.auth_attempts += 1
                # Limpa os dados parciais para forçar o cliente a reenviar
                # CPF e data de nascimento juntos na próxima tentativa.
                session._partial_cpf = None
                session._partial_birth = None
                print(f"[TRIAGEM] Falha na autenticação. Tentativa {session.auth_attempts}/{MAX_AUTH_ATTEMPTS}")
                if session.auth_attempts >= MAX_AUTH_ATTEMPTS:

                    session.status = "completed"
                    session._authenticating = False
                    msg = (
                        "Infelizmente não foi possível autenticar seus dados após várias tentativas. "
                        "Por segurança, encerramos este atendimento. Se precisar, inicie uma nova conversa."
                    )
                    session.add_message("assistant", msg)
                    print("[TRIAGEM] Atendimento encerrado por falha de autenticação (3 tentativas)")
                    return build_response(
                        session.id,
                        msg,
                        "completed",
                        False,
                        {"agent": "triage", "widget": {"kind": "closing"}},
                    )
                msg = (
                    f"Não encontrei um cadastro com esses dados. "
                    f"Tentativa {session.auth_attempts} de {MAX_AUTH_ATTEMPTS}. "
                    "Verifique o CPF e a data de nascimento e tente novamente."
                )
                session.add_message("assistant", msg)
                return build_response(
                    session.id,
                    msg,
                    "unauthenticated",
                    False,
                    {"agent": "triage", "widget": {"kind": "error", "error": MOCK_SERVICE_ERROR}},
                )
        else:
            # Cliente não está autenticando - permite conversa livre
            return _handle_pre_auth_conversation(session, message)

    # --- Cliente autenticado: identifica o assunto e redireciona ---
    intent = _llm_intent(message, session.history) or detect_intent(message)
    session.pending_intent = intent
    print(f"[TRIAGEM] Assunto identificado: {intent}")

    # Error e closing funcionam independentemente de autenticação.
    if intent == "error":
        msg = "Entendi, estamos enfrentando uma instabilidade. Tente novamente em instantes."
        session.add_message("assistant", msg)
        return build_response(
            session.id,
            msg,
            "error",
            authenticated,
            {"agent": "triage", "widget": {"kind": "error", "error": MOCK_SERVICE_ERROR}},
        )

    if intent == "closing":
        msg = "Foi um prazer ajudar. Sempre que precisar, estaremos por aqui."
        session.add_message("assistant", msg)
        return build_response(
            session.id,
            msg,
            "completed",
            authenticated,
            {"agent": "triage", "widget": {"kind": "closing"}},
        )

    # Redireciona silenciosamente para o agente adequado
    # Para consultas de crédito, delega para o agente especializado
    if intent in ("credit_limit", "credit_increase", "credit_decrease"):
        return handle_credit_message(session, message, intent)

    if intent == "exchange":
        return handle_exchange(session, message)

    if intent == "interview":
        return handle_interview(session, message)

    return _handle_authenticated_intent(session, intent, message)


def _handle_authenticated_intent(session: Session, intent: Intent, message: str) -> ChatResponse:
    """Redireciona para o agente adequado e responde como se fosse o mesmo agente.

    O redirecionamento é silencioso — o cliente não é avisado.
    """
    # Constrói o system prompt com o pré-prompt + contexto específico do intent
    system_prompt = build_triage_prompt(
        client_name=session.client.name,
        masked_document=session.client.masked_document,
        target_agent=session.agent,
        auth_status=session.status,
        intent=intent,
    )

    # Deixa claro que o cliente JÁ está autenticado — não pedir autenticação de novo.
    system_prompt += (
        f"\n\n=== STATUS DE AUTENTICAÇÃO ===\n"
        f"O cliente {session.client.name} está AUTENTICADO COM SUCESSO.\n"
        "NÃO peça CPF, data de nascimento ou qualquer dado de autenticação novamente.\n"
        "Responda diretamente à solicitação do cliente usando os dados de contexto fornecidos.\n"
        "Não mencione redirecionamento, agentes internos ou termos técnicos.\n"
        "Seja direto e útil."
    )

    widget = None

    if intent == "exchange":
        rate = select_rate(message)
        system_prompt += (
            f"\n\n## Dados de contexto\n"
            f"- Cotação: 1 {rate.base} = {rate.quote} {rate.rate} "
            f"(variação {rate.variation:+.2f}%)\n"
            "Responda de forma concisa mencionando a cotação."
        )
        widget = {"kind": "exchange_rate", "exchangeRate": to_camel_dict(rate)}
        print(f"[TRIAGEM] Redirecionando para agente: exchange")
    elif intent == "credit_limit":
        limit = _client_credit_limit(session.client)
        system_prompt += (
            f"\n\n## Dados de contexto\n"
            f"- Limite total: R$ {limit.total:,.2f}\n"
            f"- Limite disponível: R$ {limit.available:,.2f}\n"
            "Responda mencionando os limites de crédito do cliente."
        )
        widget = {"kind": "credit_limit", "creditLimit": to_camel_dict(limit)}
        print(f"[TRIAGEM] Redirecionando para agente: credit")
    elif intent == "credit_increase":
        limit = _client_credit_limit(session.client)
        system_prompt += (
            f"\n\n## Dados de contexto\n"
            f"- Limite total: R$ {limit.total:,.2f}\n"
            f"- Limite disponível: R$ {limit.available:,.2f}\n"
            "Pergunte ao cliente qual novo limite deseja solicitar."
        )
        widget = {"kind": "credit_limit", "creditLimit": to_camel_dict(limit)}
        print(f"[TRIAGEM] Redirecionando para agente: credit_increase")
    elif intent == "credit_decrease":
        limit = _client_credit_limit(session.client)
        system_prompt += (
            f"\n\n## Dados de contexto\n"
            f"- Limite total: R$ {limit.total:,.2f}\n"
            f"- Limite disponível: R$ {limit.available:,.2f}\n"
            "Pergunte ao cliente qual novo limite deseja solicitar."
        )
        widget = {"kind": "credit_limit", "creditLimit": to_camel_dict(limit)}
        print(f"[TRIAGEM] Redirecionando para agente: credit_decrease")
    elif intent == "interview":
        system_prompt += (
            "\n\n## Dados de contexto\n"
            "Você DEVE seguir EXATAMENTE estas 5 perguntas, na ordem, uma por vez:\n"
            "1. Qual é a sua renda mensal?\n"
            "2. Qual é o seu tipo de vínculo? (CLT, Autônomo, Empresário, Servidor público, Aposentado)\n"
            "3. Quanto somam suas despesas fixas?\n"
            "4. Quantos dependentes você possui?\n"
            "5. Você possui dívidas em aberto? (Não possuo / Sim, em negociação / Sim, em atraso)\n"
            "Faça apenas UMA pergunta por vez e aguarde a resposta do cliente.\n"
            "Após as 5 respostas, informe o score final e encerre a entrevista."
        )
        widget = {"kind": "interview", "questions": [q.model_dump() for q in MOCK_INTERVIEW_QUESTIONS]}
        print(f"[TRIAGEM] Redirecionando para agente: credit_interview")
    elif intent == "fallback":
        system_prompt += "\n\nConverse com o cliente de forma natural para entender o que ele precisa."
        print(f"[TRIAGEM] Redirecionando para agente: triage (fallback)")

    # Constrói mensagens para o LLM a partir do histórico
    chat_messages = [{"role": m["role"], "content": m["content"]} for m in session.history]

    llm_text = _llm_response(chat_messages, system_prompt)
    if llm_text:
        session.add_message("assistant", llm_text)
        metadata: dict = {"agent": "llm"}
        if widget:
            metadata["widget"] = widget
        return build_response(
            session.id,
            llm_text,
            "authenticated",
            True,
            metadata,
        )

    # Fallback sem LLM (respostas fixas apenas quando a chave não está configurada)
    return _fallback_response(session, intent)


def _handle_score_consult(session: Session, message: str) -> ChatResponse:
    """Consulta e exibe o score do cliente."""
    from app.services.score_service import get_credit_data
    
    cpf = getattr(session, "client_cpf", None)
    if not cpf:
        msg = "Não foi possível identificar seu CPF para consultar o score."
        session.add_message("assistant", msg)
        return build_response(session.id, msg, "authenticated", True, {"agent": "triage"})
    
    credit_data = get_credit_data(cpf)
    if credit_data is None:
        msg = "Não encontrei seu score na base de dados. Gostaria de fazer a entrevista financeira para atualizá-lo?"
        session.add_message("assistant", msg)
        return build_response(session.id, msg, "authenticated", True, {"agent": "triage"})
    
    score = credit_data["score"]
    limite_total = credit_data["limite_total"]
    
    msg = (
        f"Seu score de crédito atual é: {score}\n\n"
        f"Limite total: R$ {limite_total:,.2f}\n\n"
        "Gostaria de atualizar seu score através de uma entrevista financeira?"
    )
    session.add_message("assistant", msg)
    return build_response(
        session.id,
        msg,
        "authenticated",
        True,
        {"agent": "triage", "widget": {"kind": "score", "score": score, "limit": limite_total}},
    )


def _fallback_response(session: Session, intent: Intent) -> ChatResponse:
    """Respostas fixas de emergência quando o LLM não está disponível."""
    if intent == "exchange":
        rate = select_rate(session.pending_intent or "")
        msg = f"1 {rate.base} = {rate.quote} {rate.rate} (variação {rate.variation:+.2f}%)."
    elif intent == "credit_limit":
        limit = _client_credit_limit(session.client)
        msg = f"Seu limite é R$ {limit.available:,.2f} (total R$ {limit.total:,.2f})."
    elif intent == "credit_increase":
        limit = _client_credit_limit(session.client)
        msg = f"Seu limite atual é R$ {limit.total:,.2f}. Qual novo limite deseja solicitar?"
    elif intent == "credit_decrease":
        limit = _client_credit_limit(session.client)
        msg = f"Seu limite atual é R$ {limit.total:,.2f}. Qual novo limite deseja solicitar?"
    elif intent == "interview":
        msg = "Para atualizar seu score, me diga sua renda mensal."
    else:
        msg = "Como posso ajudar?"
    session.add_message("assistant", msg)
    return build_response(session.id, msg, "authenticated", True, {"agent": "triage"})
