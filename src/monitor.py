import argparse
import time
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from src.db import get_connection


def fetch_window_stats(last_minutes: int) -> dict:
    sql = """
    WITH recent AS (
      SELECT *
      FROM emergency_calls
      WHERE timestamp >= NOW() - (%s || ' minutes')::interval
    )
    SELECT
      COUNT(*) AS total_calls,
      SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_calls,
      AVG(latency_ms)::float AS avg_latency_ms,
      PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)::float AS p95_latency_ms
    FROM recent;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (last_minutes,))
            row = cur.fetchone() or {}
            total = int(row.get("total_calls") or 0)
            failed = int(row.get("failed_calls") or 0)
            avg_latency = row.get("avg_latency_ms")
            p95_latency = row.get("p95_latency_ms")
            failure_rate = (failed / total) if total > 0 else 0.0

            return {
                "window_minutes": last_minutes,
                "total_calls": total,
                "failed_calls": failed,
                "failure_rate": failure_rate,
                "avg_latency_ms": float(avg_latency) if avg_latency is not None else None,
                "p95_latency_ms": float(p95_latency) if p95_latency is not None else None,
            }


def fetch_worst_towers(last_minutes: int, limit: int = 3) -> list:
    sql = """
    SELECT
      tower_id,
      COUNT(*) AS total,
      SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed,
      ROUND(
        (SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*),0)) * 100,
        2
      ) AS failure_pct
    FROM emergency_calls
    WHERE timestamp >= NOW() - (%s || ' minutes')::interval
    GROUP BY tower_id
    HAVING COUNT(*) >= 3
    ORDER BY failure_pct DESC, failed DESC, total DESC
    LIMIT %s;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (last_minutes, limit))
            return cur.fetchall() or []


def classify_alert(failure_rate: float, avg_latency_ms: Optional[float], p95_latency_ms: Optional[float]) -> str:
    """
    Simple thresholds (tweakable):
      - ALERT: failure_rate >= 0.10 OR p95_latency >= 900
      - WARN:  failure_rate >= 0.05 OR avg_latency >= 600
      - OK otherwise
    """
    if p95_latency_ms is not None and p95_latency_ms >= 900:
        return "ALERT"
    if failure_rate >= 0.10:
        return "ALERT"
    if avg_latency_ms is not None and avg_latency_ms >= 600:
        return "WARN"
    if failure_rate >= 0.05:
        return "WARN"
    return "OK"


def main():
    parser = argparse.ArgumentParser(description="Monitor emergency call reliability + latency.")
    parser.add_argument("--window", type=int, default=10, help="Lookback window in minutes (default: 10)")
    parser.add_argument("--interval", type=int, default=10, help="Seconds between checks (default: 10)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    while True:
        stats = fetch_window_stats(args.window)
        worst = fetch_worst_towers(args.window, limit=3)

        level = classify_alert(stats["failure_rate"], stats["avg_latency_ms"], stats["p95_latency_ms"])

        fr_pct = round(stats["failure_rate"] * 100, 2)
        print(
            f"[{level}] last_{stats['window_minutes']}m "
            f"total={stats['total_calls']} failed={stats['failed_calls']} "
            f"failure_rate={fr_pct}% avg_latency={stats['avg_latency_ms']}ms p95={stats['p95_latency_ms']}ms"
        )

        if worst:
            print("  worst_towers:")
            for w in worst:
                print(f"    - {w['tower_id']}: failure={w['failure_pct']}% (failed={w['failed']}/{w['total']})")

        if args.once:
            break

        time.sleep(max(args.interval, 1))


if __name__ == "__main__":
    main()