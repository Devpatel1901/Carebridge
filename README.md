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


| Service             | Port | Description                                                                                                                                                    |
| ------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Brain Agent         | 8001 | LangGraph pipeline with Claude: parses discharge summaries, evaluates risk, generates disease-specific questions, analyzes responses, makes clinical decisions |
| Communication Agent | 8002 | Real Twilio SMS/Voice integration: sends follow-up questions, receives patient replies via webhooks                                                            |
| DB Agent            | 8003 | Sole database writer: persists patients, discharge data, medications, questionnaires, interactions, alerts, appointments. REST API for dashboard               |
| Scheduler           | 8004 | APScheduler: triggers follow-ups at scheduled times, subscribes to schedule events                                                                             |
| Frontend            | 3000 | Next.js dashboard: patients, alerts, appointments, timeline                                                                                                    |


### Event Flow

1. **Discharge Intake**: Hospital submits summary → Brain Agent processes with Claude (parse → extract → risk eval → generate questions → decide → emit events) → DB Agent persists → Scheduler queues follow-up
2. **Follow-up Loop**: Scheduler triggers → Communication Agent sends real SMS/voice with disease-specific questions → Patient replies → Twilio webhooks → Brain Agent analyzes responses → may alert and schedule another outbound follow-up whenever the decision is **not** `stable` (e.g. `followup_needed`, `alert`, `escalation`, `appointment_required`). Decision **`stable`** stops chaining further voice follow-ups when the patient is doing well.
3. **Dashboard**: All data visible in real-time via Next.js frontend polling DB Agent

### Follow-up scheduling (demo vs production)

- **`DEMO_MODE=true`** (default): Discharge intake always schedules the **first** outbound follow-up (Brain `scheduled_at` plus scheduler fallback). **Subsequent** voice follow-ups after a check-in are emitted when the Brain decision is **not** `stable` (symptoms often yield `alert` or `followup_needed`). Minute-scale delays (`DEMO_FOLLOWUP_MINUTES_*`) apply. If the scheduler has no `scheduled_at` on an event, it falls back to **`DEMO_FOLLOWUP_DELAY_SECONDS`** (default 240). Each job is stored in **`followup_jobs`** with **`correlation_id`**; the Communication Agent updates **status** (`pending` → `in_progress` → `completed` or `failed`) when calls start and end.
- **`DEMO_MODE=false`**: The Scheduler uses each event’s **`scheduled_at`** (wall-clock, UTC) with APScheduler. The Brain uses day/hour-based urgency delays for follow-ups it chooses to schedule (after a patient response, any non-`stable` decision can schedule another voice follow-up).

After changing the database schema, run **`uv run alembic upgrade head`** (or equivalent in Docker) so `followup_jobs` gains `correlation_id` and `completed_at`.

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

## Docker (full stack)

Run **RabbitMQ, Redis, all four Python services, the Next.js dashboard, and a persisted SQLite volume** with one command from the **repository root**:

```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY, Twilio values, and TWILIO_WEBHOOK_BASE_URL (see below)

docker compose up --build
```

- **Dashboard**: [http://localhost:3000](http://localhost:3000) — the browser calls API URLs on `localhost:8001`, `8003`, `8004` (ports published from the containers).
- **SQLite**: Stored in the Compose named volume `sqlite_data` (on disk it appears as `{project}_sqlite_data`, e.g. `carebridge_sqlite_data`). Only **db_agent** mounts it; other services use the DB Agent HTTP API (do not mount the same SQLite file on multiple writers).
- **Demo census (5 patients)**: On first startup, the **DB Agent** seeds SQLite with five patients (`1024587`, `7658321`, …). The **home page ward table** loads **`GET /patients`** only (no duplicate static JSON), so Patient IDs and Reason/Ward columns match SQLite. Each seed row includes demographics, discharge summary, medications, questionnaire, and appointments. The seed runs once per volume; to reset, remove the volume (`docker volume rm carebridge_sqlite_data`) and `docker compose up --build` again. To disable seeding, set `SKIP_DEMO_SEED=1` for the `db_agent` service (see `.env.example`).
- **Discharge upload**: The dashboard sends `existing_patient_id` to Brain `/intake` so a new discharge file **updates the same patient** instead of creating a random UUID.
- **Legacy path**: `docker compose -f infra/docker-compose.yml` loads the same stack via an `include` of the root file.

#### Steps: verify demo data after `docker compose up --build`

1. Wait until `db_agent` is healthy (logs show `demo_seed_complete` on first run, or `demo_seed_skipped` if the volume already had data).
2. Open [http://localhost:3000](http://localhost:3000), click **View Details** on e.g. David Lee (`2156793`).
3. Confirm the detail page shows **David Lee**, **Pneumonia** / recovering context from the API (not only static placeholders). Optional: call `curl -s http://localhost:8003/patients/2156793 | jq .name,.discharge_summary.diagnosis`.
4. **Re-seed from scratch**: `docker compose down`, `docker volume rm carebridge_sqlite_data`, then `docker compose up --build`.
5. **Manual seed** (local SQLite file without Docker): from repo root, `DATABASE_URL=sqlite+aiosqlite:///./carebridge.db uv run python scripts/seed_sqlite_demo.py`.

### Twilio voice + ngrok with Docker

Twilio must reach a **public HTTPS** URL. **`TWILIO_WEBHOOK_BASE_URL` must not** be `http://communication_agent:8002` (that hostname exists only inside Compose).

1. Start the stack: `docker compose up --build`.
2. On the **host**, expose published port **8002**: `ngrok http 8002`.
3. Set **`TWILIO_WEBHOOK_BASE_URL`** in `.env` to your ngrok **HTTPS** origin (no path), then restart the **communication_agent** container (or `docker compose up -d` again) so it picks up the value.

Verify TwiML is reachable:

```bash
uv run python scripts/check_twilio_tunnel.py
```

### Scripts against Docker

With default env vars, the same commands work from the **host** (they target `localhost` and the published ports):

```bash
uv run python scripts/demo_flow.py
uv run python scripts/trigger_followup.py <patient_id>
uv run python scripts/seed_data.py
```

To run the demo **inside** Compose with internal DNS (optional):

```bash
docker compose --profile tooling run --rm tooling
```

Override bases if needed (see [.env.example](.env.example)): `BRAIN_AGENT_URL`, `DB_AGENT_URL`, `SCHEDULER_URL`, `COMM_AGENT_URL`, `FRONTEND_URL`.

### Scaling note

SQLite implies a **single db_agent** instance with the data volume. To scale out multiple DB Agent replicas, move to a network database (e.g. **Postgres**) and update `DATABASE_URL` accordingly.

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

Open [http://localhost:3000](http://localhost:3000) — you should see the patient with risk level and all data populated.

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

- `POST /initiate-call` — Start SMS/voice follow-up (optional body field `schedule_correlation_id` links to a `followup_jobs` row)
- `POST /webhooks/sms` — Twilio SMS webhook
- `POST /webhooks/voice/start` — Twilio voice start
- `POST /webhooks/voice/gather` — Twilio voice input
- `GET /active-sessions`
- `GET /health`

### DB Agent (`:8003`)

- `GET /patients` — List patients
- `GET /patients/{id}` — Patient detail
- `POST /patients/{id}/schedule-followup` — Body: `{ "eastern_date": "YYYY-MM-DD", "eastern_time": "HH:MM" }` (US Eastern); publishes `schedule_event` for the scheduler (dashboard “Schedule follow-up”)
- `GET /alerts` — List alerts
- `PATCH /alerts/{id}/acknowledge` — Acknowledge alert
- `GET /appointments` — List appointments
- `GET /patients/{id}/timeline` — Patient event timeline
- `GET /patients/{id}/questionnaire` — Patient questionnaire
- `GET /followup-jobs` — List scheduled jobs
- `PATCH /followup-jobs/by-correlation/{correlation_id}` — Update job status (used by Communication Agent)
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

