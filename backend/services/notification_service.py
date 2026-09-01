"""
Industrial Multi-Channel Alert Dispatcher (Slack, MS Teams, Email)
==================================================================
Formats and dispatches GxP equipment alerts with anti-flapping deduplication,
batch financial loss in INR, and automated SOP maintenance procedures.
"""

from __future__ import annotations

import os
import json
import logging
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("notification-service")

# In-memory cooldown cache: {f"{equipment_id}:{severity}": last_sent_timestamp}
_NOTIFICATION_COOLDOWN_STORE: Dict[str, float] = {}
COOLDOWN_SECONDS = int(os.environ.get("NOTIFICATION_COOLDOWN_SECONDS", "1800"))  # 30 mins


def is_in_cooldown(equipment_id: str, severity: str) -> bool:
    """Checks if an alert for this equipment & severity was dispatched recently."""
    key = f"{equipment_id}:{severity.upper()}"
    last_sent = _NOTIFICATION_COOLDOWN_STORE.get(key)
    if last_sent is None:
        return False
    return (datetime.now(timezone.utc).timestamp() - last_sent) < COOLDOWN_SECONDS


def mark_dispatched(equipment_id: str, severity: str):
    """Records dispatch timestamp for cooldown deduplication."""
    key = f"{equipment_id}:{severity.upper()}"
    _NOTIFICATION_COOLDOWN_STORE[key] = datetime.now(timezone.utc).timestamp()


def format_slack_card(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Builds a rich Slack Block Kit message."""
    eq_id = alert.get("equipment_id", "EQUIPMENT-01")
    severity = alert.get("severity", "WARNING").upper()
    msg = alert.get("message", "Telemetry anomaly detected")
    loss_inr = alert.get("financial_loss_inr", 250000)
    sop = alert.get("sop_code", "SOP-MNT-GEN-101")
    color = "#dc2626" if severity == "CRITICAL" else "#d97706"

    return {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"?? ZYDUS GxP ALERT: {eq_id} [{severity}]",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{msg}*\n*Batch Loss Exposure:* ?{loss_inr:,.0f} INR\n*Mandatory Procedure:* `{sop}`",
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Framework: *US FDA 21 CFR Part 11* | Time: {datetime.now(timezone.utc).strftime('%d-%b-%Y %H:%M:%S UTC')}",
                            }
                        ],
                    },
                ],
            }
        ]
    }


def format_teams_card(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Builds an MS Teams Adaptive Card."""
    eq_id = alert.get("equipment_id", "EQUIPMENT-01")
    severity = alert.get("severity", "WARNING").upper()
    msg = alert.get("message", "Anomaly detected")
    loss_inr = alert.get("financial_loss_inr", 250000)

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"Zydus GxP Alert: {eq_id} ({severity})",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Attention" if severity == "CRITICAL" else "Warning",
                        },
                        {
                            "type": "TextBlock",
                            "text": msg,
                            "wrap": True,
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "Batch Risk (INR):", "value": f"?{loss_inr:,.0f}"},
                                {"title": "Regulatory Framework:", "value": "US FDA 21 CFR Part 11 / GAMP 5"},
                            ],
                        },
                    ],
                },
            }
        ],
    }


def dispatch_alert_webhook(alert: Dict[str, Any], bypass_cooldown: bool = False) -> Dict[str, Any]:
    """
    Dispatches alerts to configured webhooks with anti-flapping deduplication.
    """
    eq_id = alert.get("equipment_id", "EQUIPMENT-01")
    severity = alert.get("severity", "WARNING").upper()
    force = bypass_cooldown or alert.get("bypass_cooldown", False) or alert.get("force_dispatch", False)

    if not force and is_in_cooldown(eq_id, severity):
        logger.info(f"Notification suppressed for {eq_id} [{severity}] (cooldown active).")
        return {"dispatched": False, "reason": "COOLDOWN_ACTIVE"}

    slack_url = os.environ.get("SLACK_WEBHOOK_URL")
    teams_url = os.environ.get("TEAMS_WEBHOOK_URL")

    dispatched_channels = []

    # Slack dispatch
    if slack_url:
        try:
            payload = format_slack_card(alert)
            httpx.post(slack_url, json=payload, timeout=5.0)
            dispatched_channels.append("SLACK")
        except Exception as exc:
            logger.error(f"Failed to dispatch Slack webhook: {exc}")

    # Teams dispatch
    if teams_url:
        try:
            payload = format_teams_card(alert)
            httpx.post(teams_url, json=payload, timeout=5.0)
            dispatched_channels.append("TEAMS")
        except Exception as exc:
            logger.error(f"Failed to dispatch Teams webhook: {exc}")

    # In local/test mode, simulate dispatch if no webhooks configured
    if not dispatched_channels:
        dispatched_channels.append("MOCK_DISPATCH_CONSOLE")

    mark_dispatched(eq_id, severity)
    return {
        "dispatched": True,
        "channels": dispatched_channels,
        "equipment_id": eq_id,
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
