#!/bin/sh
set -e

if [ -n "$OTEL_EXPORTER_OTLP_ENDPOINT" ]; then
    exec opentelemetry-instrument "$@"
else
    exec "$@"
fi