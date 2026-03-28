FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
RUN uv pip install --system -e "."

COPY shared/ shared/
COPY services/ services/
COPY alembic.ini .
COPY .env .env

ARG SERVICE_MODULE=services.db_agent.main:app
ARG SERVICE_PORT=8000

ENV SERVICE_MODULE=${SERVICE_MODULE}
ENV SERVICE_PORT=${SERVICE_PORT}

EXPOSE ${SERVICE_PORT}

CMD uvicorn ${SERVICE_MODULE} --host 0.0.0.0 --port ${SERVICE_PORT}
