#!/bin/bash
set -e

echo "=================================================================="
echo "  ZYDUS PREDICTIVE MAINTENANCE - PRODUCTION BOOTSTRAP & VERIFIER  "
echo "=================================================================="

echo -e "\n[1/5] Checking Docker & Environment..."
docker --version
docker compose -f infra/docker-compose.yml up -d

echo -e "\n[2/5] Running Backend Pytest Regression..."
pytest -v

echo -e "\n[3/5] Executing Playwright E2E Verification..."
python scripts/e2e_frontend_test.py

echo -e "\n[4/5] Executing High-Availability Chaos & Failover Test..."
python scripts/ha_chaos_failover_test.py

echo -e "\n=================================================================="
echo " PRODUCTION SYSTEM DEPLOYED & 100% OPERATIONAL                     "
echo "=================================================================="
echo " • Frontend UI:          http://localhost:5173"
echo " • FastAPI Backend:      http://localhost:8000/docs"
echo " • Prometheus Metrics:   http://localhost:8000/metrics"
echo " • Airflow Webserver:    http://localhost:8080"
echo " • Grafana Dashboards:   http://localhost:3000"
echo "=================================================================="
