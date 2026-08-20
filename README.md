# QStock — Enterprise Inventory Intelligence Platform


> AI-powered inventory management platform built for Scouts Musulmans de Montréal, combining QR-based asset tracking, real-time inventory operations, role-based access control, and natural-language inventory analytics.


**250+ users** · **Python** · **FastAPI** · **PostgreSQL** · **React** · **TypeScript** · **OpenAI** · **Ollama** · **Docker**


---


## Overview


QStock is an end-to-end inventory intelligence platform designed to simplify equipment management, borrowing, returns, tracking, and operational reporting.


The platform combines traditional inventory management with an AI assistant that allows users to query structured inventory data using natural language rather than writing SQL queries manually.


The system was developed for **Scouts Musulmans de Montréal** and has supported **250+ users**.


---


## Key Capabilities


### Inventory Management


- QR-code based item identification
- Inventory search and filtering
- Borrow and return workflows
- Item history and transaction tracking
- Inventory reporting and analytics
- Item reviews and ratings


### AI Inventory Assistant


Users can ask natural-language questions about inventory in English or French.


Examples:


- "How many Dell laptops do we currently have?"
- "Which items have not been used in the last 6 months?"
- "Show me all inventory assigned to Finance."


The AI layer translates natural-language requests into database queries and returns structured results through the application.


### Security & Access Control


- JWT-based authentication
- Role-based access control
- User and administrator permissions
- Protected API endpoints
- Database-backed authorization


### Application


- Responsive React interface
- Progressive Web App support
- Real-time inventory dashboards
- QR scanning using mobile devices
- REST API
- API documentation


---


## Architecture

```text
                    ┌──────────────────────┐
                    │     React / PWA      │
                    │     TypeScript       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       FastAPI        │
                    │      REST API        │
                    └───────┬───────┬──────┘
                            │       │
                ┌───────────┘       └────────────┐
                ▼                                ▼
       ┌─────────────────┐             ┌─────────────────┐
       │   PostgreSQL    │             │   AI Assistant  │
       │   + SQLAlchemy  │             │ OpenAI / Ollama │
       └─────────────────┘             └────────┬────────┘
                                                 │
                                                 ▼
                                      Natural Language →
                                      Query Generation →
                                      Safety Validation →
                                      Database Query →
                                      Structured Response
AI Architecture

The AI assistant connects natural-language requests with structured inventory data.

User Question
     │
     ▼
Natural Language Processing
     │
     ▼
LLM Provider
(OpenAI / Ollama)
     │
     ▼
SQL Generation
     │
     ▼
Safety / Validation Layer
     │
     ▼
PostgreSQL
     │
     ▼
Structured Result
     │
     ▼
User-facing Answer

The implementation separates the AI layer from the core inventory services, allowing the application to use different model providers.

Backend Architecture

The backend is implemented with FastAPI and follows a modular service structure.

backend/
├── src/
│   ├── models/
│   ├── schemas/
│   ├── api/
│   │   └── endpoints/
│   ├── core/
│   ├── ai/
│   ├── utils/
│   └── main.py

The AI module contains the inventory assistant, SQL generation, provider integration, and safety-related logic.

Frontend

The frontend uses:

React 18
TypeScript
Vite
Material UI
React Router
html5-qrcode
date-fns

The application supports desktop and mobile workflows through responsive UI and PWA capabilities.

Security

Security-related capabilities include:

JWT authentication
Role-based access control
Protected API endpoints
Pydantic request/response validation
Database access through SQLAlchemy
Environment-based configuration
AI query safety controls

Never commit production credentials or API keys to the repository.

Deployment

The application is containerized using Docker and Docker Compose.

Core services include:

FastAPI backend
React frontend
PostgreSQL
Nginx

Example:

docker-compose up -d

API documentation is available through FastAPI's generated documentation.

Technology Stack
Backend
Python
FastAPI
PostgreSQL
SQLAlchemy
Alembic
Pydantic
JWT
AI
OpenAI APIs
Ollama
Natural-language-to-SQL workflows
Frontend
React
TypeScript
Vite
Material UI
React Router
Infrastructure
Docker
Docker Compose
Nginx
Real-World Impact

QStock was developed for Scouts Musulmans de Montréal and has supported 250+ users.

The project demonstrates the integration of:

AI + backend engineering + relational data + authentication + authorization + frontend development + deployment

rather than treating the LLM as an isolated chatbot.

Project Structure
QStock/
├── backend/
├── frontend/
├── docs/
├── scripts/
├── docker-compose.yml
├── .gitignore
└── LICENSE
Documentation

Additional documentation is available in the docs/ directory.

Setup Guide
User Guide
Administrator Guide
API Documentation
Disclaimer

This repository is provided for educational and portfolio purposes.

Production deployments should use secure secrets management, environment-specific configuration, HTTPS, database backups, monitoring, and appropriate access controls.
