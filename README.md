# CareBridge

Multi-agent, event-driven healthcare follow-up system. Built as a distributed architecture with 4 Python microservices, RabbitMQ messaging, Redis caching, SQLite persistence, and a Next.js dashboard.

## Architecture

```
Hospital → Brain Agent (LangGraph + Claude) → RabbitMQ → DB Agent → SQLite
                                                      → Scheduler → Communication Agent → Twilio SMS/Voice → Patient
                                                                                       ← Twilio Webhooks ←
Patient responses → Brain Agent (risk analysis) → Alerts → Dashboard
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| Brain Agent | 8001 | LangGraph pipeline with Claude: parses discharge summaries, evaluates risk, generates disease-specific questions, analyzes responses, makes clinical decisions |
| Communication Agent | 8002 | Real Twilio SMS/Voice integration: sends follow-up questions, receives patient replies via webhooks |
| DB Agent | 8003 | Sole database writer: persists patients, discharge data, medications, questionnaires, interactions, alerts, appointments. REST API for dashboard |
| Scheduler | 8004 | APScheduler: triggers follow-ups at scheduled times, subscribes to schedule events |
| Frontend | 3000 | Next.js dashboard: patients, alerts, appointments, timeline |

### Event Flow

1. **Discharge Intake**: Hospital submits summary → Brain Agent processes with Claude (parse → extract → risk eval → generate questions → decide → emit events) → DB Agent persists → Scheduler queues follow-up
2. **Follow-up Loop**: Scheduler triggers → Communication Agent sends real SMS with disease-specific questions → Patient replies → Twilio webhooks → Brain Agent analyzes responses → Alerts if risk detected
3. **Dashboard**: All data visible in real-time via Next.js frontend polling DB Agent

## Prerequisites

- **Python 3.12+** (installed via `uv`)
- **Node.js 22+**
- **uv** package manager
- **RabbitMQ**: `brew install rabbitmq`
- **Redis**: `brew install redis`
- **ngrok**: `brew install ngrok` (for Twilio webhooks in local dev)
- **Anthropic API key**
- **Twilio account** (Account SID, Auth Token, Phone Number)

## Setup

```bash
# 1. Clone and enter project
cd CareBridge

# 2. Create virtual environment and install dependencies
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e "."

# 3. Run database migrations
alembic upgrade head

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys:
#   ANTHROPIC_API_KEY=sk-ant-...
#   TWILIO_ACCOUNT_SID=AC...
#   TWILIO_AUTH_TOKEN=...
#   TWILIO_PHONE_NUMBER=+1...
#   TWILIO_WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok.io

# 5. Install frontend dependencies
cd frontend/nextjs-dashboard && npm install && cd ../..

# 6. Start infrastructure
brew services start rabbitmq
brew services start redis
```

## Running

You need 7 terminals (or use a process manager):

```bash
# Terminal 1: ngrok tunnel for Twilio webhooks
ngrok http 8002
# Copy the https:// URL and update TWILIO_WEBHOOK_BASE_URL in .env

# Terminal 2: DB Agent (start first - other services depend on it)
uv run uvicorn services.db_agent.main:app --port 8003 --reload

# Terminal 3: Brain Agent
uv run uvicorn services.brain_agent.main:app --port 8001 --reload

# Terminal 4: Communication Agent
uv run uvicorn services.communication_agent.main:app --port 8002 --reload

# Terminal 5: Scheduler
uv run uvicorn services.scheduler.main:app --port 8004 --reload

# Terminal 6: Frontend Dashboard
cd frontend/nextjs-dashboard && npm run dev

# Terminal 7: Run the demo
uv run python scripts/seed_data.py
```

## Demo Walkthrough

### Step 1: Seed a discharge summary
```bash
uv run python scripts/seed_data.py
```
This sends a realistic cardiac patient discharge to the Brain Agent. Claude will:
- Parse the discharge summary
- Extract medications, diagnosis, procedures
- Evaluate risk level (likely HIGH for STEMI)
- Generate 4-6 cardiac-specific follow-up questions
- Schedule follow-ups

### Step 2: Check the dashboard
Open http://localhost:3000 — you should see the patient with risk level and all data populated.

### Step 3: Trigger a follow-up
```bash
uv run python scripts/trigger_followup.py <patient_id>
```
Or use the "Trigger Follow-up SMS" button on the patient detail page. This sends real SMS to the patient's phone with the first disease-specific question.

### Step 4: Reply via SMS
Reply to the SMS from your phone. Each reply advances to the next question. After all questions are answered:
- Responses are published to RabbitMQ
- Brain Agent analyzes responses with Claude
- If risk detected → Alert created
- All data reflected in the dashboard

### Full automated demo
```bash
uv run python scripts/demo_flow.py
```

## API Reference

### Brain Agent (`:8001`)
- `POST /intake` — Process discharge summary
- `POST /evaluate-response` — Evaluate patient responses
- `GET /patients/{id}/questions` — Get generated questionnaire
- `GET /health`

### Communication Agent (`:8002`)
- `POST /initiate-call` — Start SMS/voice follow-up
- `POST /webhooks/sms` — Twilio SMS webhook
- `POST /webhooks/voice/start` — Twilio voice start
- `POST /webhooks/voice/gather` — Twilio voice input
- `GET /active-sessions`
- `GET /health`

### DB Agent (`:8003`)
- `GET /patients` — List patients
- `GET /patients/{id}` — Patient detail
- `GET /alerts` — List alerts
- `PATCH /alerts/{id}/acknowledge` — Acknowledge alert
- `GET /appointments` — List appointments
- `GET /patients/{id}/timeline` — Patient event timeline
- `GET /patients/{id}/questionnaire` — Patient questionnaire
- `GET /followup-jobs` — List scheduled jobs
- `GET /health`

### Scheduler (`:8004`)
- `GET /jobs` — List scheduled jobs
- `POST /trigger/{patient_id}` — Manual follow-up trigger
- `GET /health`

## Tech Stack

- **Python 3.12** with FastAPI (async)
- **LangGraph** for Brain Agent pipeline
- **Anthropic Claude** for all LLM operations
- **Twilio SDK** for real SMS and Voice
- **RabbitMQ** (aio-pika) for event-driven messaging
- **Redis** for session caching
- **SQLite** (aiosqlite + SQLAlchemy 2.x) for persistence
- **Alembic** for migrations
- **Next.js 14** + TypeScript + Tailwind CSS + shadcn/ui
- **structlog** for structured JSON logging with correlation IDs
- **uv** for Python dependency management
