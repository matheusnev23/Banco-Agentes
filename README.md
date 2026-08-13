# Banco Ágil

Sistema de atendimento bancário inteligente baseado em agentes de IA. O projeto é dividido em dois grandes módulos:

- **`banco-gil-chat/`** — Frontend web (React + TypeScript).
- **`banco-gil-chat/backend/`** — Backend API (Python + FastAPI).

> O backend fica **dentro** da pasta `banco-gil-chat/` propositalmente: o repositório Git está hospedado em `banco-gil-chat/`, então manter o backend ali garante que **tudo** (frontend + backend + variáveis de ambiente) seja enviado junto no commit via `git add .`. A estrutura da raiz (`package.json` + `pnpm-lock.yaml`) funciona como um **orquestrador** para rodar os dois módulos com um único comando.

---

## Visão Geral

O **Banco Ágil** é um banco digital fictício cujo atendimento é feito por um **assistente virtual conversacional**. O usuário conversa com um único agente, mas, internamente, o sistema alterna entre **4 agentes especializados**:

| Agente | Responsabilidade |
|--------|------------------|
| **Triagem** | Autentica o cliente (CPF + data de nascimento) e identifica a intenção |
| **Crédito** | Consulta limite, solicita aumento de limite |
| **Entrevista de Crédito** | Coleta dados financeiros e atualiza o score |
| **Câmbio** | Consulta cotações de moedas |

O frontend **não expõe** a troca de agentes — o cliente percebe um único assistente.

---

## Arquitetura

```
Banco Agentes/
├── package.json               # Orquestrador: roda frontend + backend juntos
├── pnpm-lock.yaml
└── banco-gil-chat/            # Repositório Git (frontend + backend)
    ├── .env                   # Variáveis do frontend
    ├── .gitignore             # Mínimo (apenas node_modules e dist)
    ├── package.json           # Dependências do frontend
    ├── pnpm-lock.yaml
    ├── src/                   # Frontend React
    │   ├── components/        # chat, credit, authentication, interview, exchange, layout, ui
    │   ├── hooks/             # useChat, use-mobile
    │   ├── pages/             # ChatPage
    │   ├── services/          # api.ts (camada HTTP), chatService.ts
    │   ├── types/             # Tipos TypeScript (Message, Client, CreditLimit...)
    │   ├── mocks/             # Dados mockados
    │   ├── routes/            # Rotas do TanStack Router
    │   └── lib/               # Utilitários (format, error-capture)
    └── backend/               # Backend Python/FastAPI
        ├── app/
        │   ├── main.py        # Entry point (CORS + rotas)
        │   ├── config.py      # Config via ambiente (pydantic-settings)
        │   ├── routers/       # auth, chat, credit, exchange, interview
        │   ├── schemas/       # Pydantic (espelham os tipos TypeScript)
        │   ├── models/        # Sessões em memória
        │   ├── agents/        # credit_agent, credit_interview_agent, exchange_agent
        │   └── services/      # agent, llm, client_db, credit_service, score_service...
        ├── data/
        │   └── clientes.csv   # Base de clientes
        ├── prompts/
        │   └── triage_prompt.txt
        ├── requirements.txt
        ├── .env / .env.example
        └── README.md
```

---

## Tecnologias e Justificativas

### Frontend — `banco-gil-chat/`

| Tecnologia | Por quê? |
|------------|-----------|
| **React 19** | Padrão de mercado para UIs interativas. Arquitetura baseada em componentes pequenos e reutilizáveis. Ecossistema maduro. |
| **TypeScript 5** | Tipagem estática em todo o frontend. Garante que os dados recebidos da API (Message, Client, CreditLimit, etc.) estejam corretos e documentados, prevenindo erros em runtime. É a ponte direta com os schemas Pydantic do backend. |
| **TanStack Router** | Roteamento tipado e filesystem-based (`src/routes/`). Menos boilerplate que React Router e com autocompleto completo das rotas. |
| **TanStack Query** | Gerenciamento de cache, retry e estados de loading/erro de chamadas HTTP. Perfeito para o futuro consumo da API FastAPI sem reescrever componentes. |
| **Tailwind CSS 4** | Estilização utilitária rápida, consistente e responsiva. O design system do Banco Ágil (azul navy, espaços em branco, sombras sutis) é expresso com classes utilitárias. |
| **Radix UI** | Componentes acessíveis e headless (Dialog, Dropdown, Tabs, etc.). Acessibilidade por padrão, estilo 100% controlado pelo Tailwind. |
| **shadcn/ui** | Conjunto de componentes criados sobre Radix + Tailwind + CVA. Acelerou a construção de componentes consistentes e acessíveis. |
| **Lucide React** | Ícones leves, consistentes e tree-shakeable. |
| **Zod** | Validação de schemas no frontend. Mesma garantia de contrato que o Pydantic dá no backend. |
| **Vite 8** | Build tool rápida (esnext-native). HMR instantâneo e startup muito veloz. |
| **React Hook Form** | Formulários performáticos e com pouca re-renderização (ex.: autenticação, aumento de limite). |
| **Recharts** | Gráficos leves para visualização de dados financeiros (score, limites). |
| **date-fns** | Manipulação de datas leve e modular (timestamps das mensagens). |
| **sonner** | Toasts elegantes para feedback ao usuário. |

**Decisão-chave de arquitetura (frontend):** a camada `src/services/api.ts` é uma **camada de transição**. Hoje as funções resolvem via `mockRequest` (dados mockados com latency simulada), mas já existe `request<T>()` preparado para `fetch` real. Trocar mocks por API FastAPI exige **apenas** alterar a camada de services — nenhum componente precisa mudar.

---

### Backend — `banco-gil-chat/backend/`

| Tecnologia | Por quê? |
|------------|-----------|
| **Python 3** | Linguagem dominante em IA/LLM. Ecossistema rico para agentes, NLP e integração com provedores de IA. |
| **FastAPI** | Framework web moderno, assíncrono e performático. Gera **Swagger/OpenAPI automático** (`/docs`), o que documenta a API sozinho. Tipagem com Pydantic garante contratos fortes. |
| **Uvicorn** | Servidor ASGI de alto desempenho para FastAPI. Suporte nativo a reload em desenvolvimento. |
| **Pydantic v2** | Validação e serialização de dados. Os schemas Pydantic **espelham exatamente** os tipos TypeScript do frontend, garantindo contrato único entre as partes. |
| **pydantic-settings** | Configuração tipada via variáveis de ambiente (`.env`). Centraliza host, porta, CORS e chaves de IA em `app/config.py`. |
| **python-dotenv** | Carrega variáveis de ambiente do `.env` em desenvolvimento. |
| **OpenAI SDK** | Integração com provedores de LLM. O `app/services/llm.py` permite **trocar de provedor** (openai, gemini, openrouter) apenas via config, sem reescrever código. |

**Decisão de arquitetura da IA:** o roteamento de intenções no `app/services/agent.py` é **baseado em regras** (determinístico) e pode ser substituído por um agente LLM real sem mudar o contrato da API. O prompt de triagem é editável em `backend/prompts/triage_prompt.txt` e suporta variáveis dinâmicas (`{{client_name}}`, `{{target_agent}}`, etc.).

**Persistência:** sessões são em memória (`app/models/session.py`). A base de clientes é carregada de `data/clientes.csv` (limites reais por cliente). Quando houver banco de dados, basta trocar a implementação do serviço — a API não muda.

---

## Decisões de Arquitetura e Justificativas

### Por que **Python**?

O Python foi escolhido como linguagem do backend por ser o **padrão de facto no ecossistema de IA/LLM**. As principais razões:

- **Ecossistema maduro de IA**: a grande maioria das bibliotecas de machine learning, processamento de linguagem natural e integração com LLMs (OpenAI, Hugging Face, etc.) é escrita em Python ou possui SDKs oficiais em Python.
- **Legibilidade e produtividade**: a sintaxe limpa do Python acelera o desenvolvimento e a manutenção, algo essencial em um projeto com múltiplos agentes de IA.
- **Comunidade e contratação**: é mais fácil encontrar desenvolvedores e documentação para soluções de IA em Python do que em qualquer outra linguagem.
- **Interoperabilidade**: integra-se facilmente com ferramentas de dados (pandas, numpy) e provedores de IA.

**Alternativas consideradas**: Node.js/TypeScript (bom para I/O assíncrono, mas ecossistema de IA menos maduro), Go (performático, mas com curva de aprendizado maior para IA) e Java (robusto, porém verboso para prototipagem rápida de agentes).

---

### Por que **FastAPI**?

O FastAPI foi escolhido como framework web por oferecer o melhor equilíbrio entre produtividade, performance e segurança:

- **Tipagem com Pydantic**: os schemas Pydantic garantem validação de dados em tempo de execução e **geram automaticamente a documentação OpenAPI/Swagger** (`/docs`). Isso significa que a API é auto-documentada e testável pelo navegador.
- **Assíncrono nativo**: suporte a `async/await` desde o início, essencial para operações de I/O intensivas como chamadas a LLMs e APIs externas.
- **Performance**: comparável a Node.js e Go em benchmarks, graças ao Starlette (ASGI).
- **Menos boilerplate**: diferente do Flask (que exige configuração manual de validação e serialização), o FastAPI entrega tudo integrado.

**Alternativas consideradas**:
- **Flask**: mais simples, mas exige bibliotecas adicionais (Flask-RESTful, marshmallow) e não tem suporte nativo a async.
- **Django/DRF**: muito completo, porém pesado para uma API de agentes; o ORM e o admin seriam subutilizados.
- **Node.js/Express**: viável, mas quebraria a consistência de usar Python no backend de IA.

---

### Por que **Lovable/React** (e não Streamlit)?

O frontend foi construído com **React + TypeScript + TanStack**, gerado e mantido pela **Lovable** (o `package.json` traz `@lovable.dev/vite-tanstack-config` e o `AGENTS.md` documenta a integração). O **Streamlit** foi avaliado e **descartado** pelas seguintes razões:

| Critério | Abordagem adotada (Lovable/React) | Streamlit |
|----------|-----------------------------------|-----------|
| **Tipo de produto** | Chat bancário com UI rica (widgets, formulários, autenticação, sidebar, indicador de digitação) | Dashboard analítico / prototipagem de dados (plots, tabelas, KPIs) |
| **Interatividade** | SPA com HMR instantâneo (Vite 8), sem recarregamento de página | Reexecuta o script a cada interação ("rerun top-to-bottom"), gerando latência |
| **Tipagem / contrato** | TypeScript espelha os schemas Pydantic (contrato único front↔back) | Roda tudo em Python, sem contrato tipado com o frontend |
| **Separação UI/API** | Camada `src/services/api.ts` troca mocks por FastAPI sem mudar componentes | UI e API se misturariam no processo Python |
| **Robustez de estado** | Estado de chat, autenticação multi-passos e widgets dinâmicos gerenciados por React | Estado em sessão do servidor, limitado para chat complexo |

**Por que a Lovable?** A plataforma acelera a construção do frontend: gera e sustenta componentes shadcn/ui, TanStack e Vite, além de oferecer preview em nuvem e edição visual — permitindo que o time de produto itere na UI rapidamente, sem escrever CSS e infraestrutura do zero. Além disso, a integração está documentada no `AGENTS.md`, que recomenda manter o histórico Git estável para sincronização com a plataforma.

**Resumo**: o projeto é um **produto web conversacional**, não um dashboard analítico. React/Lovable entrega UI rica, tipada, escalável e performática para chat em tempo real, enquanto o Streamlit ficaria restrito a prototipagem visual de dados, sem a robustez de estado, tipos e performance que o Banco Ágil exige.

---

### Por que **OpenRouter** (e não LangChain/LangGraph)?

O OpenRouter foi escolhido como **provedor de LLM** por oferecer uma **camada de abstração sobre múltiplos modelos** (OpenAI, Anthropic, Google, Meta, etc.) com uma única API. As justificativas:

- **Multi-provedor com uma linha de código**: o `app/services/llm.py` permite trocar de provedor (openai, gemini, openrouter) apenas alterando `ai_provider` no `.env`. O OpenRouter unifica isso em um único endpoint.
- **Custo-benefício**: permite testar e comparar modelos de diferentes fornecedores sem reescrever código, otimizando custo e qualidade.
- **Simplicidade**: para o escopo deste projeto (agentes com roteamento baseado em regras), o OpenRouter resolve com uma chamada HTTP simples.

**Por que não usar frameworks de agentes (ADK, CrewAI, LangChain, LangGraph, LlamaIndex)?**

Foram avaliados os principais frameworks de agentes e LLMs do mercado, mas todos foram **deliberadamente evitados** em favor de código próprio explícito. O backend tem apenas **6 dependências** (`requirements.txt`), e cada framework abaixo adicionaria complexidade e opacidade sem ganho proporcional ao escopo.

| Framework | Por que não foi usado |
|-----------|----------------------|
| **LangChain / LangGraph** | Abstrações em camadas que dificultam depuração; dezenas de dependências transitivas; fluxo "mágico" que esconde a lógica; atualizações frequentes que quebram compatibilidade. Valeria para fluxos com **múltiplos passos com estado complexo, loops de reflexão ou orquestração visual de grafos**. |
| **CrewAI** | Voltado para **equipes de agentes colaborando em paralelo** (role, goal, tasks). O Banco Ágil é roteamento conversacional em **sequência** (triagem → um agente especializado), não colaboração multiagente concorrente. Usá-lo seria over-engineering. |
| **Google ADK (Agent Developer Kit)** | Framework **muito recente** e com ecossistema menos maduro; orientado a ferramentas/tools. Aqui, as "ferramentas" são apenas chamadas internas (limite, câmbio, entrevista) resolvidas com serviços Python diretos, sem precisar de uma camada de tools. |
| **LlamaIndex** | Especializado em **RAG (Retrieval-Augmented Generation)** — indexação, embeddings e busca em bases de conhecimento. O projeto não tem "base de conhecimento corporativa": usa apenas `clientes.csv` + sessões em memória. Incluiria infra de ingestão/busca sem demandá-la. |

**Comparação direta (LangChain/LangGraph vs. abordagem adotada):**

| Critério | Abordagem adotada (código próprio) | LangChain/LangGraph |
|----------|-------------------------------------|---------------------|
| **Complexidade** | Código explícito e rastreável, fácil de debugar | Abstrações em camadas que dificultam o rastreamento de erros |
| **Dependências** | Apenas `openai` SDK | Dezenas de dependências transitivas |
| **Controle** | Controle total sobre o fluxo de agentes | Comportamento "mágico" que esconde a lógica |
| **Manutenção** | Fácil de estender e testar | Atualizações frequentes que quebram compatibilidade |
| **Transparência** | O roteamento de intenções é explícito no `agent.py` | O fluxo fica implícito na configuração do framework |

**Quando valeria a pena usar esses frameworks?** Se o projeto evoluísse para fluxos com **múltiplos passos com estado complexo, loops de reflexão, orquestração visual de grafos de agentes (LangGraph), equipes de agentes autônomas (CrewAI) ou RAG sobre uma base de conhecimento corporativa (LlamaIndex)**, eles trariam valor. Para o cenário atual (agentes com roteamento determinístico e prompts editáveis), a complexidade adicional não se justifica.

**Conclusão**: a arquitetura foi desenhada para ser **simples, transparente e fácil de evoluir**. Se no futuro for necessário orquestrar agentes mais complexos, a camada de serviços (`app/services/`) pode ser refatorada para usar qualquer um desses frameworks **sem alterar a API nem o frontend**.

---

## Como executar

### Pré-requisitos
- **Node.js** (para o frontend)
- **pnpm** (gerenciador de pacotes)
- **Python 3.10+** (para o backend)

### Passo a passo

**1. Instalar dependências (orquestrador + frontend + backend):**

```bash
cd "Banco Agentes"
pnpm install                 # instala do root e do frontend
cd banco-gil-chat/backend
pip install -r requirements.txt
cd ../..
```

> O script `install:all` no `package.json` da raiz faz isso automaticamente:
> ```bash
> pnpm install && cd banco-gil-chat/backend && pip install -r requirements.txt
> ```

**2. Configurar variáveis de ambiente:**

```bash
# Backend
cd banco-gil-chat/backend
copy .env.example .env   # Windows
# ou
cp .env.example .env     # Linux/Mac
```

**3. Rodar tudo (frontend + backend juntos):**

```bash
cd "Banco Agentes"
pnpm dev
```

Isso executa, em paralelo:
- Backend: `cd banco-gil-chat/backend && uvicorn app.main:app --reload --port 8000`
- Frontend: `cd banco-gil-chat && pnpm dev`

**4. Acessar:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Documentação Swagger: http://localhost:8000/docs
- Health check: http://localhost:8000/health

---

## Endpoints da API

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

---

## Autenticação (agente de triagem)

O agente de triagem autentica o cliente usando **CPF + data de nascimento**, direto do texto da conversa. Os clientes ficam em `banco-gil-chat/backend/data/clientes.csv`:

```csv
nome,cpf,data_nascimento,limite_total,limite_disponivel
Marina Duarte,11144477735,1988-03-15,8000,5000
João Santos,52998224725,1995-07-22,12000,9000
```

- `cpf` aceita com ou sem pontuação.
- `data_nascimento` aceita `YYYY-MM-DD` ou `dd/mm/aaaa`.
- O agente concede **3 tentativas** de autenticação; após isso, encerra por segurança.

Após autenticar, o **agente de triagem** roteia para o agente apropriado conforme a intenção:
- `credit` → limite / cartão / fatura
- `credit_increase` → aumento de limite
- `credit_interview` → score / entrevista financeira
- `exchange` → cotação de moedas

---

## Pré-prompt do agente

O pré-prompt do agente de triagem fica em `banco-gil-chat/backend/prompts/triage_prompt.txt` (100% editável). Suporta variáveis dinâmicas:

| Variável | Descrição |
|----------|-----------|
| `{{client_name}}` | Nome completo do cliente |
| `{{masked_document}}` | CPF mascarado (ex: `***.***.777-**`) |
| `{{target_agent}}` | Agente de destino detectado |
| `{{auth_status}}` | Status da autenticação |
| `{{intent}}` | Intenção detectada na mensagem |

---

## Estrutura de componentes (frontend)

```
src/
├── components/
│   ├── chat/          # ChatWindow, ChatMessage, ChatInput, TypingIndicator, QuickActions
│   ├── credit/        # CreditLimitCard, CreditIncreaseForm, CreditRequestStatus
│   ├── authentication/# AuthenticationForm
│   ├── interview/     # InterviewCard, ScoreCard
│   ├── exchange/      # ExchangeRateCard
│   ├── layout/        # Sidebar, Header, MainLayout
│   ├── common/        # StatusBadge, LoadingState, ErrorState
│   └── ui/            # Componentes shadcn/ui (Radix + Tailwind)
├── hooks/             # useChat, use-mobile
├── pages/             # ChatPage
├── services/          # api.ts, chatService.ts
├── types/             # Message, Client, CreditLimit, ExchangeRate...
├── mocks/             # bancoAgil.ts
├── routes/            # Rotas TanStack
└── lib/               # format, error-capture, utils
```

---

## Notas técnicas relevantes

- **Monorepo leve**: a raiz usa `pnpm` com `package.json` orquestrador; o frontend tem seu próprio `package.json`. Isso permite rodar ambos com `pnpm dev`.
- **Contrato único between front/back**: os types TypeScript (`src/types/index.ts`) espelham os schemas Pydantic (`backend/app/schemas/`). Alterar a API reflete em ambos os lados.
- **IA plugável**: o backend suporta OpenAI, Gemini e OpenRouter apenas mudando `ai_provider` no `.env`.
- **Fluxo 100% conversacional**: widgets (caixas) são apenas informativos (limite, cotação). A coleta de dados (CPF, renda) é feita em texto natural pela conversa.