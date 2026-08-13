# Banco Ágil - Backend (FastAPI)

API do assistente virtual do **Banco Ágil**. Este backend fornece os endpoints que o frontend `banco-gil-chat` consome.

## Estrutura

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Entry point do FastAPI (CORS + rotas)
│   ├── config.py            # Configurações via variáveis de ambiente
│   ├── routers/             # Rotas da API (chat, auth, credit, interview, exchange)
│   ├── schemas/             # Schemas Pydantic (espelham os tipos TypeScript)
│   ├── models/              # Modelos de dados (sessões em memória)
│   └── services/            # Lógica de negócio (agente, crédito, entrevista, câmbio)
├── data/
│   └── clientes.csv         # Base de clientes (nome, CPF, data de nascimento, limite)
├── requirements.txt
├── .env                     # Variáveis de ambiente
└── .env.example             # Exemplo de configuração
```

## Como executar

### 1. Criar ambiente virtual (recomendado)

```bash
cd backend
python -m venv venv
```

Ativar no Windows:
```bash
venv\Scripts\activate
```

Ativar no Linux/Mac:
```bash
source venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
copy .env.example .env    # Windows
# ou
cp .env.example .env      # Linux/Mac
```

### 4. Rodar o servidor

```bash
uvicorn app.main:app --reload
```

O servidor estará disponível em:
- **API**: http://localhost:8000
- **Docs (Swagger)**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/chat` | Envia mensagem e recebe resposta do agente (com widgets) |
| POST | `/api/chat/start` | Inicia uma nova conversa |
| POST | `/api/auth` | Autentica o cliente (CPF + data de nascimento) |
| GET | `/api/credit/limit?session_id=` | Consulta limite de crédito |
| POST | `/api/credit/increase` | Solicita aumento de limite |
| GET | `/api/interview/questions` | Retorna perguntas da entrevista financeira |
| POST | `/api/interview` | Submete respostas e recebe score |
| GET | `/api/exchange/rate?base=USD&quote=BRL` | Consulta cotação de moedas |
| GET | `/health` | Verificação de saúde da API |

## Integração com o Frontend

O frontend `banco-gil-chat` já está preparado para consumir esta API:

1. Defina a URL base no frontend:
   ```
   VITE_API_BASE_URL=http://localhost:8000
   ```

2. O `src/services/chatService.ts` já consome a API real via `request<T>()` (sem mocks).

3. Os schemas da API espelham exatamente os tipos em `src/types/index.ts`, então não é necessário mudar componentes.

## Autenticação (agente de triagem)

O agente de triagem autentica o cliente usando **CPF + data de nascimento**.
Os clientes cadastrados ficam em `data/clientes.csv`, com o formato:

```csv
nome,cpf,data_nascimento,limite_total,limite_disponivel
Marina Duarte,11144477735,1988-03-15,8000,5000
João Santos,52998224725,1995-07-22,12000,9000
Ana Pereira,98765432100,1982-11-10,15000,15000
Carlos Oliveira,12345678909,1990-02-05,6000,2000
Matheus Neves,45573022890,2003-12-23,10000,7500
```

- `cpf` aceita com ou sem pontuação (`111.444.777-35` ou `11144477735`).
- `data_nascimento` aceita `YYYY-MM-DD` (formato do CSV) ou `dd/mm/aaaa` (formato do formulário).
- `limite_total` e `limite_disponivel` são os limites de crédito do cliente (números, sem separador de milhar).

Após a autenticação, o **agente de triagem** direciona o cliente para o agente apropriado com base na **intenção detectada** na mensagem:
- `credit` → limite de crédito / cartão / fatura
- `credit_increase` → aumento de limite
- `credit_interview` → atualização de score / entrevista financeira
- `exchange` → cotação de moedas

## Pré-prompt do agente de AI

O pré-prompt do agente de triagem fica em `backend/prompts/triage_prompt.txt`.
Ele é **100% editável** — edite o arquivo para ajustar o comportamento da IA.

Suporta **variáveis dinâmicas** substituídas automaticamente a cada conversa:

| Variável | Descrição |
|----------|-----------|
| `{{client_name}}` | Nome completo do cliente |
| `{{masked_document}}` | CPF mascarado (ex: `***.***.777-**`) |
| `{{target_agent}}` | Agente de destino detectado |
| `{{auth_status}}` | Status da autenticação |
| `{{intent}}` | Intenção detectada na mensagem |

O serviço `app/services/prompt_service.py` carrega o template, substitui as variáveis
e injeta como system prompt quando `OPENAI_API_KEY` está configurada.

## Notas

- As **sessões são armazenadas em memória** (`app/models/session.py`), incluindo o histórico da conversa. Quando houver banco de dados, basta trocar essa implementação.
- A **base de clientes** (`data/clientes.csv`) é lida pelo serviço `app/services/client_db.py` e inclui os limites de crédito de cada cliente.
- Os limites de crédito são lidos do CSV em vez de valores mockados fixos. As demais informações (cotações, score) ainda são **mockadas** nos services.
- O **fluxo é 100% conversacional**: a autenticação extrai CPF e data de nascimento diretamente do texto do usuário (não há formulário). As caixas (widgets) são usadas apenas para exibir informações (limite, cotação), nunca para coletar dados.
- O agente concede **3 tentativas de autenticação**; se excedidas, o atendimento é encerrado por segurança.
- O **roteamento de intenções** do agente fica em `app/services/agent.py` e espelha a lógica do frontend. Pode ser substituído por um LLM/agente real.
