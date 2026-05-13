"""OpenTelemetry SDK bootstrap for the timetable service (R12)."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI


def init_telemetry(app: FastAPI) -> None:
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

    service_name = os.getenv("OTEL_SERVICE_NAME", "iut-timetable")
    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)

    try:
        from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
        PymongoInstrumentor().instrument()
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
    except ImportError:
        pass
