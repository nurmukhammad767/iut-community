"""OpenTelemetry SDK bootstrap (R12).

Call `init_telemetry(app)` once at FastAPI startup. Reads the standard
`OTEL_*` environment variables, so all behavior is controlled from
docker-compose without code changes.

This wires up:
  - traces  → OTLP/HTTP exporter to the LGTM collector
  - metrics → OTLP/HTTP exporter (Prometheus visible inside Grafana)
  - logs    → OTLP/HTTP exporter (Loki visible inside Grafana)
  - auto-instrumentation: FastAPI, SQLAlchemy, PyMongo, Redis, Requests
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import FastAPI


def init_telemetry(app: FastAPI, *, sqlalchemy_engine=None) -> None:
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:  # pragma: no cover
        logging.warning("OpenTelemetry not installed; skipping init: %s", exc)
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "iut-app")
    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)

    _safe_instrument_sqlalchemy(sqlalchemy_engine)
    _safe_instrument_pymongo()
    _safe_instrument_redis()
    _safe_instrument_requests()


def _safe_instrument_sqlalchemy(engine) -> None:
    if engine is None:
        return
    try:
        from opentelemetry.instrumentation.sqlalchemy import (
            SQLAlchemyInstrumentor,
        )
        SQLAlchemyInstrumentor().instrument(engine=engine)
    except ImportError:
        pass


def _safe_instrument_pymongo() -> None:
    try:
        from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
        PymongoInstrumentor().instrument()
    except ImportError:
        pass


def _safe_instrument_redis() -> None:
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
    except ImportError:
        pass


def _safe_instrument_requests() -> None:
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        RequestsInstrumentor().instrument()
    except ImportError:
        pass
