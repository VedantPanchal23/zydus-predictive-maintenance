"""
Prometheus Metrics Registry
===========================
Provides standardized Prometheus exposition metrics for telemetry throughput,
inference latency, active alerts, and database pool utilization.
"""

from __future__ import annotations

import time
from typing import Dict


class MetricsRegistry:
    def __init__(self):
        self.telemetry_ingest_total = 0
        self.telemetry_dlq_total = 0
        self.inference_total = 0
        self.inference_duration_sum = 0.0
        self.active_websocket_connections = 0
        self.active_critical_alerts = 0
        self.active_warning_alerts = 0

    def inc_ingest(self, count: int = 1):
        self.telemetry_ingest_total += count

    def inc_dlq(self, count: int = 1):
        self.telemetry_dlq_total += count

    def observe_inference(self, duration_seconds: float):
        self.inference_total += 1
        self.inference_duration_sum += duration_seconds

    def set_ws_connections(self, count: int):
        self.active_websocket_connections = count

    def set_alerts(self, critical: int, warning: int):
        self.active_critical_alerts = critical
        self.active_warning_alerts = warning

    def generate_prometheus_output(self) -> str:
        avg_inf_latency = (
            self.inference_duration_sum / self.inference_total
            if self.inference_total > 0
            else 0.0
        )
        lines = [
            "# HELP pdm_telemetry_ingest_total Total count of raw telemetry readings ingested",
            "# TYPE pdm_telemetry_ingest_total counter",
            f"pdm_telemetry_ingest_total {self.telemetry_ingest_total}",
            "",
            "# HELP pdm_telemetry_dlq_total Total corrupt or rejected readings routed to Dead Letter Queue",
            "# TYPE pdm_telemetry_dlq_total counter",
            f"pdm_telemetry_dlq_total {self.telemetry_dlq_total}",
            "",
            "# HELP pdm_inference_total Total ML inference prediction cycles executed",
            "# TYPE pdm_inference_total counter",
            f"pdm_inference_total {self.inference_total}",
            "",
            "# HELP pdm_inference_avg_latency_seconds Average duration of ML inference cycles in seconds",
            "# TYPE pdm_inference_avg_latency_seconds gauge",
            f"pdm_inference_avg_latency_seconds {avg_inf_latency:.6f}",
            "",
            "# HELP pdm_active_websocket_connections Current active WebSocket client subscriptions",
            "# TYPE pdm_active_websocket_connections gauge",
            f"pdm_active_websocket_connections {self.active_websocket_connections}",
            "",
            "# HELP pdm_active_alerts Active alert count partitioned by severity",
            "# TYPE pdm_active_alerts gauge",
            f'pdm_active_alerts{{severity="CRITICAL"}} {self.active_critical_alerts}',
            f'pdm_active_alerts{{severity="WARNING"}} {self.active_warning_alerts}',
        ]
        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()
