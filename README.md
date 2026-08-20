# QStock — Enterprise Inventory Intelligence Platform

> **Production-oriented AI engineering platform for inventory intelligence, operational workflows, and natural-language access to structured business data.**

**250+ users** · **Python** · **FastAPI** · **PostgreSQL** · **React/TypeScript** · **OpenAI** · **Ollama** · **Docker** · **GitHub Actions**

---

## Why QStock?

QStock is an end-to-end inventory intelligence platform built for **Scouts Musulmans de Montréal** and used by **250+ users**.

The platform combines conventional inventory operations with an AI assistant that lets users ask questions about structured operational data in natural language. Instead of exposing raw SQL to users, QStock applies an AI workflow that routes requests, generates or selects safe queries, validates them, executes read-only database operations, and produces grounded user-facing responses.

The project was engineered as an application—not as an isolated LLM demo—with authentication, authorization, database integration, frontend workflows, AI safety controls, evaluation, performance instrumentation, automated testing, and CI/CD quality gates.

---

## Highlights

### 🤖 AI-powered inventory assistant

- Natural-language interaction with structured inventory data
- English and French query handling
- Intent classification and routing
- Template-based SQL generation for predictable queries
- LLM-assisted SQL generation for more complex requests
- Read-only SQL execution
- Grounded response generation
- Follow-up conversation support
- OpenAI and Ollama provider support

### 🛡️ AI & data safety

- Prompt-injection defenses
- Untrusted-input boundaries
- SQL safety validation
- Destructive-query protection
- Sensitive-column restrictions
- Read-only database execution
- Input validation and bounded request size
- Environment-based secret configuration

### 📊 AI evaluation & reliability

- Versioned AI evaluation dataset
- Intent classification regression tests
- SQL safety regression tests
- Multilingual test cases
- Follow-up query scenarios
- Prompt-injection test cases
- Deterministic test suite that does not require external LLM calls
- AI regression tests integrated into CI

### ⚡ Performance & cost awareness

QStock instruments the AI workflow to measure:

- p50 / p95 latency
- LLM call count
- Input/output token usage
- Estimated model cost
- SQL-template hit rate
- Deterministic-response rate
- Pipeline-level timing

The architecture deliberately avoids unnecessary LLM calls when deterministic or template-based processing is sufficient.

### 🏭 Production engineering

- FastAPI REST backend
- React/TypeScript frontend
- PostgreSQL persistence
- Docker / Docker Compose
- GitHub Actions CI
- Backend linting and automated tests
- Frontend production build validation
- Docker build validation
- Dependabot dependency monitoring
- Production deployment and rollback runbook

---

## Architecture

```text
                         ┌─────────────────────────┐
                         │       React / PWA       │
                         │      TypeScript UI      │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │         FastAPI         │
                         │       REST API          │
                         └────────────┬────────────┘
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                         ▼                         ▼
                ┌─────────────────┐      ┌─────────────────────┐
                │   PostgreSQL    │      │    AI Assistant      │
                │ SQLAlchemy / DB │      │ OpenAI / Ollama      │
                └─────────────────┘      └──────────┬──────────┘
                                                     │
                                                     ▼
                                           ┌─────────────────────┐
                                           │ Input / Policy      │
                                           └──────────┬──────────┘
                                                      │
                                                      ▼
                                           ┌─────────────────────┐
                                           │ Intent Classification│
                                           └──────────┬──────────┘
                                                      │
                                      ┌───────────────┴───────────────┐
                                      │                               │
                                      ▼                               ▼
                              Template Match                  LLM SQL Generation
                                      │                               │
                                      └───────────────┬───────────────┘
                                                      ▼
                                           ┌─────────────────────┐
                                           │    SQL Guard        │
                                           │ safety / policy     │
                                           └──────────┬──────────┘
                                                      ▼
                                           ┌─────────────────────┐
                                           │ Read-only Executor  │
                                           └──────────┬──────────┘
                                                      ▼
                                           ┌─────────────────────┐
                                           │ Grounded Response   │
                                           │ / deterministic     │
                                           └──────────┬──────────┘
                                                      ▼
                                                 User Answer
```

---

## AI Request Lifecycle

A typical inventory question follows this path:

```text
User question
     │
     ▼
Input normalization & policy checks
     │
     ▼
Intent classification
     │
     ├── General / procedural → controlled conversational response
     │
     └── Inventory query
             │
             ▼
       Template matching
             │
        ┌────┴────┐
        │         │
       HIT       MISS
        │         │
        ▼         ▼
   Safe SQL   LLM SQL generation
        │         │
        └────┬────┘
             ▼
        SQL validation
             │
             ▼
       Read-only execution
             │
             ▼
      Structured database data
             │
             ▼
   Deterministic or grounded answer
```

This design reduces unnecessary model calls while keeping the LLM behind explicit application-level controls.

---

## Core AI Engineering Decisions

### 1. Template-first query generation

Known inventory questions can be resolved through predefined query templates instead of invoking an LLM. This reduces latency, model usage, and cost while improving determinism.

### 2. LLM-assisted SQL with application validation

For requests that cannot be handled by templates, the LLM can generate SQL. Generated SQL is treated as **untrusted output** and must pass application-level validation before execution.

### 3. Defense in depth

QStock does not rely on prompt instructions as its only security mechanism. AI-generated SQL is protected by application-level validation, read-only execution policies, query restrictions, and database access controls.

### 4. Grounded responses

The assistant is designed to answer inventory questions from retrieved database results rather than inventing operational facts.

### 5. Provider abstraction

The application supports both hosted and locally running models through **OpenAI and Ollama**, allowing experimentation with different deployment and cost models.

---

## Evaluation

QStock includes a versioned evaluation dataset covering representative AI behaviors such as:

- English inventory questions
- French inventory questions
- General/procedural questions
- Follow-up questions
- SQL safety violations
- Sensitive-data requests
- Prompt-injection attempts

The regression suite measures deterministic behaviors such as intent routing and SQL safety without requiring an external LLM service.

For live model evaluation, the project tracks the dimensions required to evaluate production AI behavior:

```text
Intent accuracy
SQL validity
SQL execution success
Answer correctness
Answer groundedness
p50 / p95 latency
LLM calls
Token usage
Estimated cost
```

The repository intentionally does not claim production accuracy or cost figures that have not been measured against a representative live workload.

---

## Security

Security is treated as a system property rather than a prompt-only feature.

- JWT authentication
- Role-based access control
- Protected API endpoints
- Pydantic validation
- Environment-based secrets
- SQL safety validation
- Read-only AI database workflow
- Sensitive-column restrictions
- Prompt-injection defenses
- Bounded AI input
- No production credentials in source control

See [`SECURITY.md`](SECURITY.md) for the vulnerability reporting policy.

---

## Performance & Observability

The AI pipeline records operational metrics without storing prompts, SQL statements, user IDs, or email addresses in the performance collector.

Tracked metrics include:

- request latency
- p50 / p95 latency
- LLM invocation count
- token usage
- estimated cost
- template hit rate
- deterministic answer rate
- pipeline stage timings

See [`docs/AI_PERFORMANCE.md`](docs/AI_PERFORMANCE.md) for details.

---

## Application Capabilities

### Inventory

- QR-code asset identification
- Inventory search and filtering
- Borrow / return workflows
- Item history and transaction tracking
- Reporting and operational analytics
- Item reviews and ratings

### User experience

- Responsive React interface
- Progressive Web App support
- Mobile QR scanning
- Real-time inventory dashboards
- REST API
- FastAPI-generated API documentation

### Access control

- JWT authentication
- Role-based authorization
- User and administrator permissions
- Protected application endpoints

---

## Technology Stack

| Layer | Technologies |
|---|---|
| AI | OpenAI APIs, Ollama, LLM orchestration, natural-language-to-SQL |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database | PostgreSQL |
| Frontend | React, TypeScript, Vite, Material UI, React Router |
| Infrastructure | Docker, Docker Compose, Nginx |
| Quality | Pytest, Ruff, GitHub Actions |
| Security | JWT, RBAC, SQL validation, environment-based secrets |

---

## Project Structure

```text
QStock/
├── backend/
│   ├── src/
│   │   ├── ai/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── main.py
│   └── tests/
├── frontend/
├── docs/
├── scripts/
├── .github/
│   ├── workflows/
│   └── dependabot.yml
├── docker-compose.yml
├── SECURITY.md
└── README.md
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker / Docker Compose
- PostgreSQL (or the provided Docker setup)
- An OpenAI API key and/or a local Ollama installation, depending on the selected AI provider

### Configuration

Copy the example environment configuration and provide local values:

```bash
cp .env.example .env
```

**Never commit `.env` or production credentials.**

### Run with Docker

```bash
docker compose up -d
```

### Backend tests

```bash
cd backend
pytest -q
```

### Backend linting

```bash
cd backend
ruff check src tests
```

### Frontend

```bash
cd frontend
npm ci
npm run build
```

---

## CI/CD

Every pull request targeting `main` is designed to pass automated quality gates covering:

```text
Python compilation
      ↓
Ruff linting
      ↓
Backend tests + AI regression tests
      ↓
Frontend production build
      ↓
Docker Compose validation
      ↓
Backend container build
```

Dependency updates are monitored through Dependabot.

See [`docs/CI_CD.md`](docs/CI_CD.md) and [`docs/PRODUCTION_RUNBOOK.md`](docs/PRODUCTION_RUNBOOK.md).

---

## Real-World Impact

QStock was developed for **Scouts Musulmans de Montréal** and has supported **250+ users**.

The project demonstrates end-to-end engineering across:

**AI systems · backend services · relational data · security · frontend applications · evaluation · observability · performance · CI/CD**

The goal is not simply to expose an LLM through a chat interface, but to integrate AI into a controlled operational software system.

---

## Engineering Focus

QStock is primarily a portfolio project demonstrating practical **AI Engineering / Applied AI Engineering** capabilities:

- production-oriented LLM integration
- AI orchestration
- natural-language interaction with structured enterprise data
- AI safety and guardrails
- deterministic vs. model-driven workflows
- AI evaluation and regression testing
- latency and cost instrumentation
- containerization and CI/CD
- full-stack system integration

---

## Documentation

Additional project documentation is available under [`docs/`](docs/), including setup, user, administrator, AI quality, AI performance, CI/CD, and production runbook documentation.

---

## Disclaimer

QStock is provided as an engineering and portfolio project. Production deployments should use managed secret storage, HTTPS, environment-specific configuration, database backups, monitoring, least-privilege access, and an appropriate deployment platform.

## License

MIT
