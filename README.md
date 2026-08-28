# QStock — Enterprise Inventory Intelligence Platform

> **Production-oriented AI engineering platform for natural-language access to structured inventory data, secure NL→SQL, operational workflows, and measurable AI reliability.**

**250+ users** · **Python** · **FastAPI** · **PostgreSQL** · **React/TypeScript** · **OpenAI** · **Ollama** · **Docker** · **GitHub Actions**

---

## Overview

QStock is an end-to-end inventory intelligence platform developed for **Scouts Musulmans de Montréal** and used by **250+ users**.

The platform combines inventory operations with an AI assistant that allows users to ask questions about structured business data in natural language. Instead of exposing raw SQL directly to users, QStock applies a controlled **natural-language-to-SQL (NL→SQL)** workflow with deterministic routing, reusable query templates, LLM-assisted generation for harder requests, SQL validation, read-only execution, and grounded responses.

QStock is engineered as a complete application rather than an isolated LLM demo, combining AI orchestration, relational data, authentication, authorization, frontend workflows, safety controls, evaluation, observability, automated testing, and CI/CD.

## Why QStock?

A useful enterprise AI system must do more than generate plausible text. It must:

- understand the user's intent
- access the correct structured data
- constrain untrusted model output
- protect sensitive operations
- return grounded results
- remain testable and observable
- control model latency and cost

QStock demonstrates this approach through a **template-first, policy-controlled AI query architecture**.

---

## AI Architecture

```text
                         User Question
                              │
                              ▼
                   Input / Policy Validation
                              │
                              ▼
                     Intent Classification
                              │
                  ┌───────────┴───────────┐
                  │                       │
                  ▼                       ▼
          General / Procedural      Inventory Query
                  │                       │
                  ▼                       ▼
          Controlled Response       Template Matching
                                          │
                                   ┌──────┴──────┐
                                   │             │
                                  HIT           MISS
                                   │             │
                                   ▼             ▼
                              Safe SQL     LLM SQL Generation
                                   │             │
                                   └──────┬──────┘
                                          ▼
                                   SQL Guard / Policy
                                          │
                                          ▼
                                  Read-only Executor
                                          │
                                          ▼
                                  Structured Results
                                          │
                                          ▼
                             Grounded / Deterministic Answer
```

This architecture deliberately keeps the LLM behind application-level controls. Model output is treated as **untrusted input**, not as an authorization mechanism.

---

## Core AI Engineering Decisions

### Template-first NL→SQL

Frequently requested inventory operations are resolved through predefined query templates. This improves determinism, reduces unnecessary LLM calls, lowers latency, and controls cost.

### LLM fallback for complex requests

Requests that cannot be resolved deterministically can use LLM-assisted SQL generation. Generated SQL must pass validation before it can reach the database.

### Defense in depth

QStock does not rely on a system prompt to enforce database security. It combines application-level validation, query restrictions, read-only execution, protected columns, and database access controls.

### Grounded answers

Inventory answers are generated from structured database results rather than allowing the model to invent operational facts.

### Provider abstraction

QStock supports hosted and locally running model providers through **OpenAI and Ollama**, allowing different development, privacy, deployment, and cost configurations.

---

## Safety & Security

Security is treated as a system property.

- JWT authentication
- Role-based access control
- Protected API endpoints
- Pydantic input validation
- Environment-based secret configuration
- SQL safety validation
- Read-only AI database workflow
- Sensitive-column restrictions
- Prompt-injection defenses
- Bounded AI input
- No production credentials in source control

The AI assistant is intentionally prevented from becoming a general-purpose unrestricted database interface.

See [`SECURITY.md`](SECURITY.md) for the vulnerability reporting policy.

---

## AI Evaluation & Reliability

QStock includes a versioned evaluation and regression suite covering:

- English inventory questions
- French inventory questions
- General/procedural questions
- Follow-up queries
- SQL safety violations
- Sensitive-data requests
- Prompt-injection attempts

Deterministic regression tests do not require external LLM calls, making them suitable for repeatable CI execution.

For live AI evaluation, the system tracks the dimensions required to assess production behavior:

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

The repository intentionally avoids unsupported production accuracy or cost claims. Performance numbers should be reported only when measured against representative workloads.

---

## Performance & Observability

The AI pipeline instruments operational behavior, including:

- request latency
- p50 / p95 latency
- LLM invocation count
- input/output token usage
- estimated model cost
- template hit rate
- deterministic response rate
- pipeline stage timing

The performance collector is designed not to store prompts, generated SQL, user IDs, or email addresses as telemetry payloads.

See [`docs/AI_PERFORMANCE.md`](docs/AI_PERFORMANCE.md) for details.

---

## Production Engineering

QStock integrates AI into a conventional software engineering stack:

```text
React / TypeScript
        │
        ▼
     FastAPI
        │
   ┌────┴────┐
   ▼         ▼
PostgreSQL   AI Orchestrator
             │
             ├── Intent routing
             ├── Templates
             ├── LLM provider
             ├── SQL validation
             └── Grounded response

Docker / Compose
        │
GitHub Actions
        │
Automated tests + builds
```

Production-oriented engineering practices include:

- Docker / Docker Compose
- GitHub Actions CI
- Backend linting and automated tests
- Frontend production build validation
- Docker build validation
- Dependabot dependency monitoring
- Production deployment and rollback documentation

---

## Application Capabilities

### Inventory

- QR-code asset identification
- Inventory search and filtering
- Borrow / return workflows
- Item history and transaction tracking
- Reporting and operational analytics
- Item reviews and ratings

### AI Assistant

- Natural-language inventory queries
- English and French interaction
- Intent classification
- Template-based SQL
- LLM-assisted SQL
- Follow-up conversation support
- Grounded responses
- OpenAI / Ollama provider support

### User Experience

- Responsive React interface
- Progressive Web App support
- Mobile QR scanning
- Real-time inventory dashboards
- REST API
- FastAPI-generated API documentation

---

## Technology Stack

| Layer | Technologies |
|---|---|
| AI | OpenAI APIs, Ollama, LLM orchestration, NL→SQL |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database | PostgreSQL |
| Frontend | React, TypeScript, Vite, Material UI, React Router |
| Infrastructure | Docker, Docker Compose, Nginx |
| Quality | Pytest, Ruff, GitHub Actions |
| Security | JWT, RBAC, SQL validation, environment-based secrets |

---

## Testing & CI/CD

The repository includes automated quality gates for the major application layers:

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
- PostgreSQL, or the provided Docker setup
- An OpenAI API key and/or a local Ollama installation, depending on the selected provider

### Configuration

```bash
cp .env.example .env
```

Never commit `.env` or production credentials.

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

## Real-World Impact

QStock was developed for **Scouts Musulmans de Montréal** and has supported **250+ users**.

This makes QStock particularly valuable as an AI engineering portfolio project because the AI layer is integrated into an operational application with real users rather than presented only as a standalone prototype.

The project demonstrates:

**AI systems · NL→SQL · backend engineering · relational data · security · frontend applications · evaluation · observability · performance · CI/CD**

---

## Engineering Focus

QStock demonstrates practical **AI Engineering / Applied AI Engineering** capabilities across the full system lifecycle:

- production-oriented LLM integration
- natural-language interaction with structured enterprise data
- deterministic and model-driven AI workflows
- AI safety and guardrails
- secure NL→SQL
- AI evaluation and regression testing
- latency and cost instrumentation
- containerization and CI/CD
- full-stack system integration

---

## Documentation

Additional documentation is available under [`docs/`](docs/), including setup, user, administrator, AI quality, AI performance, CI/CD, and production runbook documentation.

---

## Disclaimer

QStock is an engineering and portfolio project. Production deployments should use managed secret storage, HTTPS, environment-specific configuration, database backups, monitoring, least-privilege access, and an appropriate deployment platform.

## License

MIT
