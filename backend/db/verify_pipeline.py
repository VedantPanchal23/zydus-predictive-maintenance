"""
Pipeline Verification Script
=============================
Connects to TimescaleDB and verifies the data pipeline is working.

Usage (from project root):
    python backend/db/verify_pipeline.py
"""

import os
import sys
import psycopg2
import httpx
from datetime import datetime


DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://zydus_user:zydus_pass@localhost:5432/zydus_db",
)


def verify():
    print()
    print("Pipeline verification report")
    print("─" * 45)

    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
    except Exception as e:
        print(f"✗ Cannot connect to database: {e}")
        sys.exit(1)

    # Total readings
    cur.execute("SELECT COUNT(*) FROM sensor_readings")
    total = cur.fetchone()[0]
    print(f"Total readings in DB       : {total:,}")

    # Unique equipment reporting
    cur.execute("""
        SELECT COUNT(DISTINCT e.name)
        FROM sensor_readings sr
        JOIN equipment e ON sr.equipment_id = e.id
    """)
    reporting = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM equipment")
    total_eq = cur.fetchone()[0]
    print(f"Unique equipment reporting : {reporting} / {total_eq}")

    # Latest reading
    cur.execute("SELECT MAX(timestamp) FROM sensor_readings")
    latest = cur.fetchone()[0]
    if latest:
        print(f"Latest reading timestamp   : {latest.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"Latest reading timestamp   : None")

    # Readings per equipment
    print(f"\nReadings per equipment:")
    cur.execute("""
        SELECT e.name, COUNT(sr.id) as cnt
        FROM equipment e
        LEFT JOIN sensor_readings sr ON e.id = sr.equipment_id
        GROUP BY e.name
        ORDER BY e.name
    """)
    rows = cur.fetchall()
    for name, cnt in rows:
        print(f"  {name:<18}: {cnt:,} readings")

    # Anomaly detection (check if readings are outside normal ranges)
    cur.execute("""
        SELECT COUNT(*)
        FROM sensor_readings
        WHERE value < 0 OR value > 100000
    """)
    anomalies = cur.fetchone()[0]
    print(f"\nAnomalous values detected  : {anomalies:,}")

    # Open-Meteo API check
    print()
    try:
        resp = httpx.get(
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=22.99&longitude=72.60&current=temperature_2m",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        temp = data["current"]["temperature_2m"]
        print(f"Open-Meteo API working     : YES (latest ambient temp: {temp}°C)")
    except Exception as e:
        print(f"Open-Meteo API working     : NO ({e})")

    # Status
    print()
    if total > 0 and reporting == total_eq:
        print("✅ Pipeline is HEALTHY")
    elif total > 0:
        print(f"⚠️  Pipeline is PARTIAL — only {reporting}/{total_eq} equipment reporting")
    else:
        print("❌ Pipeline has NO DATA — check simulator and Kafka consumer")

    cur.close()
    conn.close()
    print()


if __name__ == "__main__":
    verify()
