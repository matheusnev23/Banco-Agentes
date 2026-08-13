"""Agente de entrevista de crédito.

Realiza uma entrevista conversacional estruturada com o cliente para coletar
dados financeiros e recalcular seu score de crédito com base em uma fórmula ponderada.
"""

import csv
import re
import unicodedata
from pathlib import Path
from typing import Optional

from app.models.session import Session
from app.schemas.chat import ChatResponse
from app.schemas.interview import InterviewQuestion
from app.services.prompt_service import build_triage_prompt
from app.services.llm import llm_response as _llm_response_for_interview
from app.utils import to_camel_dict

# Caminho do CSV de clientes
CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "clientes.csv"

# Pesos da fórmula de score
PESO_RENDA = 30
PESO_EMPREGO = {
    "formal": 300,
    "autonomo": 200,
    "desempregado": 0,
}
PESO_DEPENDENTES = {
    0: 100,
    1: 80,
    2: 60,
    "3+": 30,
}
PESO_DIVIDAS = {
    "sim": -100,
    "nao": 100,
}

# Mapeamento de opções de emprego para chaves do peso
EMPREGO_MAP = {
    "clt": "formal",
    "formal": "formal",
    "autonomo": "autonomo",
    "empresario": "autonomo",
    "servidor publico": "formal",
    "aposentado": "formal",
}

# Mapeamento de opções de dívidas
DIVIDA_MAP = {
    "nao possuo": "nao",
    "sim, em negociacao": "sim",
    "sim, em atraso": "sim",
    "sim": "sim",
    "nao": "nao",
}


def _log_agent(message: str) -> None:
    """Imprime no console qual agente está atendendo."""
    print(f"[AGENTE ENTREVISTA] {message}")


def _build_response(session_id: str, message: str, status: str, authenticated: bool, metadata: dict) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        message=message,
        status=status,
        authenticated=authenticated,
        metadata=metadata,
    )


def _parse_br_number(text: str) -> float | None:
    """Converte um número em formato brasileiro para float."""
    text = text.strip().replace("R$", "").strip()
    if not text:
        return None

    if text.lower().endswith("k"):
        number_part = text[:-1].strip()
        value = _parse_br_number(number_part)
        if value is not None:
            return value * 1000
        return None

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


def _extract_value_with_llm(session: Session, message: str, field_name: str) -> float | None:
    """Usa LLM para extrair um valor numérico de uma resposta em linguagem natural."""
    # Primeiro tenta o parser numérico direto
    direct = _parse_br_number(message)
    if direct is not None:
        return direct

    # Se não conseguiu, usa LLM para extrair
    system_prompt = (
        "Você é um extrator de dados financeiros. "
        f"Extraia o valor da {field_name} da mensagem do cliente. "
        "Retorne APENAS o número (ex: 2500, 3500.5). "
        "Se não encontrar, retorne 'null'."
    )
    chat_messages = [{"role": "user", "content": message}]
    llm_text = _llm_response_for_interview(chat_messages, system_prompt)
    if llm_text:
        cleaned = llm_text.strip().replace("R$", "").replace(".", "").replace(",", ".").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _extract_employment_with_llm(session: Session, message: str) -> str | None:
    """Usa LLM para extrair o tipo de emprego de uma resposta em linguagem natural."""
    # Primeiro tenta o mapeamento direto
    normalized = unicodedata.normalize("NFD", message.strip().lower())
    normalized = re.sub(r"[\u0300-\u036f]", "", normalized)
    direct = EMPREGO_MAP.get(normalized)
    if direct:
        return direct

    # Se não conseguiu, usa LLM
    system_prompt = (
        "Você é um extrator de dados financeiros. "
        "Classifique o tipo de vínculo do cliente em uma destas opções: "
        "CLT, Autônomo, Empresário, Servidor público, Aposentado. "
        "Retorne APENAS a opção escolhida."
    )
    chat_messages = [{"role": "user", "content": message}]
    llm_text = _llm_response_for_interview(chat_messages, system_prompt)
    if llm_text:
        normalized_llm = unicodedata.normalize("NFD", llm_text.strip().lower())
        normalized_llm = re.sub(r"[\u0300-\u036f]", "", normalized_llm)
        return EMPREGO_MAP.get(normalized_llm)
    return None


def _extract_debts_with_llm(session: Session, message: str) -> str | None:
    """Usa LLM para extrair se o cliente tem dívidas."""
    system_prompt = (
        "Você é um extrator de dados financeiros. "
        "O cliente possui dívidas em aberto? "
        "Responda APENAS 'sim' ou 'nao'."
    )
    chat_messages = [{"role": "user", "content": message}]
    llm_text = _llm_response_for_interview(chat_messages, system_prompt)
    if llm_text:
        normalized = unicodedata.normalize("NFD", llm_text.strip().lower())
        normalized = re.sub(r"[\u0300-\u036f]", "", normalized)
        if "sim" in normalized:
            return "sim"
        if "nao" in normalized or "não" in normalized:
            return "nao"
    return None


def _normalize_cpf(cpf: str) -> str:
    """Remove pontuação do CPF."""
    return re.sub(r"\D", "", cpf or "")


def _load_clients() -> list[dict]:
    """Lê todos os clientes do CSV como dicts."""
    if not CSV_PATH.exists():
        return []

    clients: list[dict] = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clients.append(dict(row))
    return clients


def _save_clients(rows: list[dict]) -> None:
    """Salva a lista de dicts no CSV."""
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _get_client_row(cpf: str) -> Optional[dict]:
    """Busca a linha do cliente no CSV pelo CPF."""
    normalized = _normalize_cpf(cpf)
    for row in _load_clients():
        if _normalize_cpf(row.get("cpf", "")) == normalized:
            return row
    return None


def _update_client_score(cpf: str, novo_score: int) -> bool:
    """Atualiza o campo score do cliente no CSV."""
    normalized = _normalize_cpf(cpf)
    rows = _load_clients()
    updated = False

    for row in rows:
        if _normalize_cpf(row.get("cpf", "")) == normalized:
            row["score"] = str(novo_score)
            updated = True
            break

    if updated:
        _save_clients(rows)
        # Invalida o cache do client_db para que get_clients() re-leia o arquivo
        import app.services.client_db as client_db
        client_db._cache = None

    return updated


def _calculate_score(renda: float, despesas: float, tipo_emprego: str, dependentes: int, tem_dividas: bool) -> int:
    """Calcula o score de crédito usando a fórmula ponderada."""
    # Normaliza tipo de emprego
    emprego_key = EMPREGO_MAP.get(tipo_emprego.lower(), "desempregado")
    peso_emprego = PESO_EMPREGO.get(emprego_key, 0)

    # Normaliza dependentes
    if dependentes >= 3:
        peso_dep = PESO_DEPENDENTES["3+"]
    else:
        peso_dep = PESO_DEPENDENTES.get(dependentes, 0)

    # Normaliza dívidas
    tem_dividas_str = "sim" if tem_dividas else "nao"
    peso_div = PESO_DIVIDAS.get(tem_dividas_str, 0)

    # Fórmula
    score = (renda / (despesas + 1)) * PESO_RENDA + peso_emprego + peso_dep + peso_div

    # Garante que está entre 0 e 1000
    return max(0, min(1000, int(score)))


def _get_score_band(score: int) -> str:
    """Retorna a faixa do score."""
    if score < 500:
        return "low"
    if score < 800:
        return "medium"
    return "high"


# Estado da entrevesta
class InterviewState:
    """Armazena o estado da entrevista para uma sessão."""
    def __init__(self) -> None:
        self.current_step = 0
        self.income: Optional[float] = None
        self.employment: Optional[str] = None
        self.expenses: Optional[float] = None
        self.dependents: Optional[int] = None
        self.has_debts: Optional[bool] = None
        self.completed = False
        self.final_score: Optional[int] = None
        self.started = False


# Perguntas da entrevista
INTERVIEW_QUESTIONS: list[InterviewQuestion] = [
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


def _get_interview_state(session: Session) -> InterviewState:
    """Recupera ou cria o estado da entrevista na sessão."""
    if not hasattr(session, "_interview_state") or session._interview_state is None:
        session._interview_state = InterviewState()
    return session._interview_state


def _is_question_or_doubt(message: str) -> bool:
    """Verifica se a mensagem parece ser uma pergunta ou dúvida, não uma resposta direta."""
    normalized = unicodedata.normalize("NFD", message.strip().lower())
    normalized = re.sub(r"[\u0300-\u036f]", "", normalized)
    
    # Palavras que indicam pergunta
    question_indicators = [
        "?", "como", "o que", "qual", "quando", "onde", "por que", "porque",
        "pode", "poderia", "gostaria", "saber", "entender", "duvida", "dúvida",
        "importante", "significa", "explica", "explicar", "ajuda", "ajudar",
    ]
    
    # Se tem ponto de interrogação, é uma pergunta
    if "?" in message:
        return True
    
    # Se começa com palavras de pergunta
    for indicator in question_indicators:
        if normalized.startswith(indicator):
            return True
    
    # Se contém palavras de pergunta no meio
    for indicator in question_indicators[3:]:  # exclui "como", "o que", "qual" que podem ser respostas
        if f" {indicator} " in f" {normalized} ":
            return True
    
    return False


def _handle_interview_doubt(session: Session, message: str) -> ChatResponse:
    """Responde uma dúvida do cliente durante a entrevista e REPETE a pergunta atual."""
    state = _get_interview_state(session)
    current_q = INTERVIEW_QUESTIONS[state.current_step]
    
    # Responde a dúvida usando LLM
    system_prompt = (
        "Você é o agente de entrevista de crédito do Banco Ágil. "
        f"O cliente está na pergunta: {current_q.label} "
        "Responda a dúvida/pergunta do cliente de forma clara e útil. "
        "Após responder, peça para ele continuar com a pergunta da entrevista. "
        "Seja conciso e amigável."
    )
    chat_messages = [{"role": m["role"], "content": m["content"]} for m in session.history]
    llm_text = _llm_response_for_interview(chat_messages, system_prompt)
    
    if llm_text:
        session.add_message("assistant", llm_text)
        # Agora repete a pergunta atual
        if current_q.kind == "choice":
            follow_up = f"\n\n{current_q.label}\nOpções: {', '.join(current_q.options)}"
        else:
            follow_up = f"\n\n{current_q.label}"
        
        # Adiciona a pergunta novamente como uma nova mensagem
        session.add_message("assistant", follow_up)
        
        return _build_response(
            session.id,
            llm_text + follow_up,
            "authenticated",
            True,
            {"agent": "credit_interview"},
        )
    
    # Fallback sem LLM
    msg = (
        f"Entendi sua dúvida. Vamos continuar?\n\n"
        f"{current_q.label}\n"
        f"Opções: {', '.join(current_q.options) if current_q.options else 'informe um valor numérico'}"
    )
    session.add_message("assistant", msg)
    return _build_response(session.id, msg, "authenticated", True, {"agent": "credit_interview"})


def _handle_interview_step(session: Session, message: str) -> ChatResponse:
    """Processa um passo da entrevista com ajuda do LLM para respostas naturais."""
    state = _get_interview_state(session)

    # Se já completou, limpa o agente ativo e retorna para o triage
    if state.completed:
        session.active_agent = None
        return _build_response(
            session.id,
            "A entrevista já foi concluída. Como posso ajudar com mais alguma coisa?",
            "authenticated",
            True,
            {"agent": "credit_interview"},
        )

    # Verifica se é uma pergunta/dúvida (não uma resposta direta)
    if _is_question_or_doubt(message):
        print(f"[ENTREVISTA] Cliente fez uma pergunta: {message[:50]}")
        return _handle_interview_doubt(session, message)

    # Processa a resposta atual
    current_q = INTERVIEW_QUESTIONS[state.current_step]
    answer_valid = True

    if current_q.id == "income":
        value = _extract_value_with_llm(session, message, "renda mensal")
        if value is None or value <= 0:
            answer_valid = False
        else:
            state.income = value

    elif current_q.id == "employment":
        emprego_normalizado = _extract_employment_with_llm(session, message)
        if not emprego_normalizado:
            answer_valid = False
        else:
            state.employment = emprego_normalizado

    elif current_q.id == "expenses":
        value = _extract_value_with_llm(session, message, "despesas fixas")
        if value is None or value < 0:
            answer_valid = False
        else:
            state.expenses = value

    elif current_q.id == "dependents":
        value = _extract_value_with_llm(session, message, "dependentes")
        if value is None or value < 0 or value != int(value):
            answer_valid = False
        else:
            state.dependents = int(value)

    elif current_q.id == "debts":
        normalized_answer = unicodedata.normalize("NFD", message.strip().lower())
        normalized_answer = re.sub(r"[\u0300-\u036f]", "", normalized_answer)
        divida_key = DIVIDA_MAP.get(normalized_answer)
        if divida_key is None:
            # Tenta extrair com LLM
            divida_key = _extract_debts_with_llm(session, message)
            if divida_key is None:
                answer_valid = False
            else:
                state.has_debts = divida_key == "sim"
        else:
            state.has_debts = divida_key == "sim"

    # Se a resposta for inválida, pede novamente de forma natural via LLM
    if not answer_valid:
        system_prompt = (
            "Você é o agente de entrevista de crédito do Banco Ágil. "
            "A resposta do cliente não ficou clara. "
            f"Pergunte novamente: {current_q.label} "
            f"Opções válidas: {', '.join(current_q.options) if current_q.options else 'informe um valor numérico'}."
        )
        chat_messages = [{"role": m["role"], "content": m["content"]} for m in session.history]
        llm_text = _llm_response_for_interview(chat_messages, system_prompt)
        
        if llm_text:
            session.add_message("assistant", llm_text)
            return _build_response(session.id, llm_text, "authenticated", True, {"agent": "credit_interview"})
        
        msg = f"Por favor, informe um valor válido. {current_q.label}"
        session.add_message("assistant", msg)
        return _build_response(session.id, msg, "authenticated", True, {"agent": "credit_interview"})

    # Avança para a próxima pergunta
    state.current_step += 1

    # Se terminou todas as perguntas, calcula o score
    if state.current_step >= len(INTERVIEW_QUESTIONS):
        state.completed = True
        # Limpa o agente ativo - entrevista concluída
        session.active_agent = None
        score = _calculate_score(
            renda=state.income or 0,
            despesas=state.expenses or 0,
            tipo_emprego=state.employment or "desempregado",
            dependentes=state.dependents or 0,
            tem_dividas=state.has_debts or False,
        )
        state.final_score = score

        # Atualiza o score no CSV
        if session.client_cpf:
            _update_client_score(session.client_cpf, score)

        band = _get_score_band(score)

        # Mensagem de conclusão - texto exato, sem LLM
        msg = (
            f"Obrigado por completar a entrevista!\n\n"
            f"Seu novo score de crédito é: {score} (faixa: {band}).\n\n"
            "Seu score foi atualizado em nosso sistema. "
            "Posso ajudar com mais alguma coisa?"
        )
        session.add_message("assistant", msg)
        return _build_response(
            session.id,
            msg,
            "authenticated",
            True,
            {"agent": "credit_interview", "score": score, "band": band},
        )

    # Caso contrário, faz a próxima pergunta de forma natural via LLM
    next_q = INTERVIEW_QUESTIONS[state.current_step]
    
    # Usa LLM para gerar a pergunta, mas EXIGE que use o texto exato no FINAL
    system_prompt = (
        "Você é o agente de entrevista de crédito do Banco Ágil. "
        "Faça uma breve introdução amigável e depois faça A PERGUNTA EXATA abaixo.\n\n"
        f"PERGUNTA EXATA (use exatamente este texto): {next_q.label}\n"
    )
    if next_q.options:
        system_prompt += f"Opções (liste exatamente assim): {', '.join(next_q.options)}\n"
    system_prompt += (
        "\nREGRA: Sua resposta DEVE conter o texto exato da pergunta acima. "
        "NÃO inventar perguntas diferentes. "
        "Exemplo: \"Perfeito! Agora me diga: Qual é a sua renda mensal?\"\n"
    )
    
    chat_messages = [{"role": m["role"], "content": m["content"]} for m in session.history]
    llm_text = _llm_response_for_interview(chat_messages, system_prompt)
    
    if llm_text and next_q.label.lower() in llm_text.lower():
        session.add_message("assistant", llm_text)
        return _build_response(session.id, llm_text, "authenticated", True, {"agent": "credit_interview"})
    
    # Fallback sem LLM - texto exato
    if next_q.kind == "choice":
        msg = f"{next_q.label}\nOpções: {', '.join(next_q.options)}"
    else:
        msg = next_q.label
    
    session.add_message("assistant", msg)
    return _build_response(session.id, msg, "authenticated", True, {"agent": "credit_interview"})


def handle_interview(session: Session, message: str) -> ChatResponse:
    """Processa uma mensagem no fluxo da entrevista de crédito."""
    _log_agent(f"ATENDENDO ENTREVISTA — sessão: {session.id} | cliente: {session.client.name if session.client else 'N/A'}")

    if session.client is None:
        return _build_response(
            session.id,
            "Preciso que você esteja autenticado para realizar a entrevista de crédito.",
            "unauthenticated",
            False,
            {"agent": "credit_interview"},
        )

    # Verifica se o usuário quer REFAZER a entrevista (mesmo que já completou)
    if "refazer" in message.lower() or "novamente" in message.lower() or "de novo" in message.lower():
        session._interview_state = InterviewState()
        session.active_agent = "credit_interview"
        _log_agent("Usuário solicitou refazer a entrevista. Reiniciando estado.")
        # Primeira pergunta - texto exato, sem LLM
        first_q = INTERVIEW_QUESTIONS[0]
        msg = first_q.label
        session.add_message("assistant", msg)
        return _build_response(session.id, msg, "authenticated", True, {"agent": "credit_interview"})

    # Verifica se é a primeira mensagem (início da entrevista)
    state = _get_interview_state(session)
    if not state.completed and not state.started:
        state.started = True
        # Marca o agente ativo para que o triage não intercepte as respostas
        session.active_agent = "credit_interview"
        # Primeira pergunta - texto exato, sem LLM
        first_q = INTERVIEW_QUESTIONS[0]
        msg = first_q.label
        session.add_message("assistant", msg)
        return _build_response(session.id, msg, "authenticated", True, {"agent": "credit_interview"})

    # Processa a resposta e avança
    return _handle_interview_step(session, message)


def get_questions() -> list[InterviewQuestion]:
    """Retorna as perguntas da entrevista financeira."""
    return INTERVIEW_QUESTIONS


def submit_answers(session_id: str, answers: dict[str, str]) -> dict:
    """Processa as respostas da entrevista e calcula o score (via API)."""
    from app.models.session import session_store
    session = session_store.get(session_id)
    if not session or session.client is None:
        raise ValueError("Sessão não encontrada ou cliente não autenticado")

    # Preenche as respostas
    for q in INTERVIEW_QUESTIONS:
        if q.id == "income":
            val = _parse_br_number(answers.get("income", ""))
            if val is not None:
                state = _get_interview_state(session)
                state.income = val
        elif q.id == "employment":
            state = _get_interview_state(session)
            state.employment = EMPREGO_MAP.get(answers.get("employment", "").lower(), "desempregado")
        elif q.id == "expenses":
            val = _parse_br_number(answers.get("expenses", ""))
            if val is not None:
                state = _get_interview_state(session)
                state.expenses = val
        elif q.id == "dependents":
            val = _parse_br_number(answers.get("dependents", ""))
            if val is not None:
                state = _get_interview_state(session)
                state.dependents = int(val)
        elif q.id == "debts":
            state = _get_interview_state(session)
            divida_key = DIVIDA_MAP.get(answers.get("debts", "").lower())
            state.has_debts = divida_key == "sim" if divida_key else False

    # Calcula o score
    state = _get_interview_state(session)
    score = _calculate_score(
        renda=state.income or 0,
        despesas=state.expenses or 0,
        tipo_emprego=state.employment or "desempregado",
        dependentes=state.dependents or 0,
        tem_dividas=state.has_debts or False,
    )
    state.final_score = score
    state.completed = True
    # Limpa o agente ativo - entrevista concluída via API
    session.active_agent = None

    # Atualiza no CSV
    if session.client_cpf:
        _update_client_score(session.client_cpf, score)

    band = _get_score_band(score)
    questions = [q.model_copy(update={"answer": answers.get(q.id, "")}) for q in INTERVIEW_QUESTIONS]

    return {
        "score": {"value": score, "max": 1000, "band": band},
        "questions": [q.model_dump() for q in questions],
    }
