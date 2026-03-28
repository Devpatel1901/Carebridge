from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import aio_pika
from pydantic import BaseModel

from shared.config import get_settings
from shared.logging import correlation_id_ctx, get_logger

logger = get_logger("event_bus")

EXCHANGE_NAME = "carebridge"


class EventBus:
    def __init__(self) -> None:
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def connect(self) -> None:
        settings = get_settings()
        self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            EXCHANGE_NAME,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        logger.info("event_bus_connected", exchange=EXCHANGE_NAME)

    async def disconnect(self) -> None:
        if self._channel:
            await self._channel.close()
        if self._connection:
            await self._connection.close()
        logger.info("event_bus_disconnected")

    @property
    def exchange(self) -> aio_pika.abc.AbstractExchange:
        if not self._exchange:
            raise RuntimeError("EventBus not connected. Call connect() first.")
        return self._exchange

    @property
    def channel(self) -> aio_pika.abc.AbstractChannel:
        if not self._channel:
            raise RuntimeError("EventBus not connected. Call connect() first.")
        return self._channel

    async def publish(
        self,
        event_name: str,
        payload: BaseModel,
        correlation_id: str | None = None,
        source_service: str = "unknown",
    ) -> None:
        cid = correlation_id or correlation_id_ctx.get("") or str(uuid.uuid4())
        envelope = {
            "event_type": event_name,
            "correlation_id": cid,
            "source_service": source_service,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload.model_dump(mode="json"),
        }
        message = aio_pika.Message(
            body=json.dumps(envelope).encode(),
            content_type="application/json",
            headers={"correlation_id": cid},
        )
        await self.exchange.publish(message, routing_key=event_name)
        logger.info(
            "event_published",
            event_type=event_name,
            correlation_id=cid,
        )

    async def subscribe(
        self,
        event_name: str,
        handler: Callable[[dict[str, Any]], Any],
        queue_name: str | None = None,
    ) -> None:
        q_name = queue_name or f"{event_name}_queue"
        queue = await self.channel.declare_queue(q_name, durable=True)
        await queue.bind(self.exchange, routing_key=event_name)

        async def _on_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
            async with message.process():
                try:
                    envelope = json.loads(message.body.decode())
                    cid = envelope.get("correlation_id", "")
                    correlation_id_ctx.set(cid)
                    logger.info(
                        "event_received",
                        event_type=event_name,
                        correlation_id=cid,
                    )
                    await handler(envelope)
                except Exception:
                    logger.exception("event_handler_error", event_type=event_name)

        await queue.consume(_on_message)
        logger.info("event_subscribed", event_type=event_name, queue=q_name)


event_bus = EventBus()
