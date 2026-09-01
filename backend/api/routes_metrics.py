"""
REST API: Health Probes & Prometheus Metrics
============================================
Kubernetes probes (/health/live, /health/ready) and Prometheus (/metrics).
"""

from __future__ import annotations

import logging
import os
from fastapi import APIRouter, Response, status

import redis as redis_lib
from core.db_pool import get_db_cursor
from core.metrics import metrics
from core.config import REDIS_URL

logger = logging.getLogger("metrics-router")
router = APIRouter(tags=["Observability & Health"])


@router.get("/metrics")
async def prometheus_metrics():
    """Exposes real-time Prometheus scrape metrics."""
    content = metrics.generate_prometheus_output()
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")


@router.get("/health")
async def standard_health():
    """Basic healthcheck endpoint."""
    return {"status": "ok", "service": "zydus-backend", "version": "3.0.0"}


@router.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe(response: Response):
    """Kubernetes readiness probe verifying PostgreSQL and Redis connections."""
    db_ok = False
    redis_ok = False

    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT 1;")
            db_ok = True
    except Exception as exc:
        logger.error("Readiness DB check failed: %s", exc)

    try:
        r = redis_lib.from_url(REDIS_URL, socket_timeout=2)
        r.ping()
        redis_ok = True
    except Exception as exc:
        logger.error("Readiness Redis check failed: %s", exc)

    if db_ok and redis_ok:
        return {"status": "ready", "database": "healthy", "cache": "healthy"}
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "database": "healthy" if db_ok else "unreachable",
            "cache": "healthy" if redis_ok else "unreachable",
        }
