"""OpenTelemetry SDK bootstrap (R12).

Call `init_telemetry(app)` once at FastAPI startup. Reads the standard
`OTEL_*` environment variables, so all behavior is controlled from
docker-compose without code changes.

Wires up:
  - traces  -> OTLP/HTTP exporter to the LGTM collector (Tempo)
  - metrics -> OTLP/HTTP exporter (Prometheus visible inside Grafana)
  - logs    -> OTLP/HTTP exporter (Loki visible inside Grafana) by
               attaching a LoggingHandler to the root Python logger so
               every `logging.info(...)` / `logger.error(...)` flows out
  - auto-instrumentation: FastAPI, SQLAlchemy, PyMongo, Redis, Requests
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI


def init_telemetry(app: FastAPI, *, sqlalchemy_engine=None) -> None:
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return

    try:
        from opentelemetry import trace
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import (
            OTLPLogExporter,
        )
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.metrics import set_meter_provider
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:  # pragma: no cover
        logging.warning("OpenTelemetry not installed; skipping init: %s", exc)
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "iut-app")
    resource = Resource.create({"service.name": service_name})

    # --- Traces ---
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(trace_provider)

    # --- Metrics ---
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(), export_interval_millis=15000
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    set_meter_provider(meter_provider)

    # --- Logs (root logger -> OTLP -> Loki via collector) ---
    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(log_provider)

    otel_handler = LoggingHandler(level=logging.INFO, logger_provider=log_provider)
    otel_handler.setFormatter(
        logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )
    root = logging.getLogger()
    root.addHandler(otel_handler)
    if root.level > logging.INFO or root.level == logging.NOTSET:
        root.setLevel(logging.INFO)
    # uvicorn's own loggers don't propagate to root by default
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.INFO)
        lg.addHandler(otel_handler)
        lg.propagate = True

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
