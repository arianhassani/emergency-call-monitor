import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    """
    Opens a Postgres connection using env vars.
    """
    return psycopg2.connect(
        dbname=os.getenv("PGDATABASE", "emergency_db"),
        user=os.getenv("PGUSER", os.getenv("USER", "postgres")),
        password=os.getenv("PGPASSWORD", ""),  # empty if you use local trust auth
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
    )


def insert_emergency_call(call: dict) -> int:
    """
    Inserts one call event. Returns call_id.
    Expected keys:
      timestamp, caller_id, tower_id, latency_ms, status, failure_reason
    """
    sql = """
    INSERT INTO emergency_calls (timestamp, caller_id, tower_id, latency_ms, status, failure_reason)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING call_id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    call["timestamp"],
                    call["caller_id"],
                    call["tower_id"],
                    call["latency_ms"],
                    call["status"],
                    call.get("failure_reason"),
                ),
            )
            return cur.fetchone()[0]


def fetch_summary(last_minutes: int = 10) -> dict:
    """
    Returns basic monitoring stats over the last N minutes.
    """
    sql = """
    WITH recent AS (
      SELECT *
      FROM emergency_calls
      WHERE timestamp >= NOW() - (%s || ' minutes')::interval
    )
    SELECT
      COUNT(*) AS total_calls,
      SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_calls,
      AVG(latency_ms)::float AS avg_latency_ms
    FROM recent;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (last_minutes,))
            row = cur.fetchone() or {}
            total = int(row.get("total_calls") or 0)
            failed = int(row.get("failed_calls") or 0)
            avg_latency = row.get("avg_latency_ms")
            failure_rate = (failed / total) if total > 0 else 0.0
            return {
                "window_minutes": last_minutes,
                "total_calls": total,
                "failed_calls": failed,
                "failure_rate": failure_rate,
                "avg_latency_ms": float(avg_latency) if avg_latency is not None else None,
            }