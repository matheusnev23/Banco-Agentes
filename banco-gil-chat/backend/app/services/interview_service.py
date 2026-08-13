"""Serviço da entrevista financeira."""

from app.schemas.interview import CreditScore, InterviewQuestion, InterviewResponse

# Perguntas padrão da entrevista financeira.
# TODO: carregar de banco de dados / configuração
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


def get_questions() -> list[InterviewQuestion]:
    """Retorna as perguntas da entrevista financeira."""
    return INTERVIEW_QUESTIONS


def submit_answers(session_id: str, answers: dict[str, str]) -> InterviewResponse:
    """Processa as respostas e calcula o score de crédito."""
    # TODO: integrar com modelo de scoring real
    questions = [q.model_copy(update={"answer": answers.get(q.id, "")}) for q in INTERVIEW_QUESTIONS]
    score = CreditScore(value=742, band="high")
    return InterviewResponse(score=score, questions=questions)