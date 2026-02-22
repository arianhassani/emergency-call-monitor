# Emergency Call Monitoring Simulator

Backend service that simulates emergency call events (e.g. 000), stores them in PostgreSQL, and runs monitoring queries to detect elevated failure rates and latency spikes.

Models basic reliability and operational monitoring patterns used in telecom environments.

---

## Overview

The system consists of two CLI components.

### Call Generator

- Produces synthetic emergency call events  
- Configurable event rate and failure probability  
- Injects simulated failure reasons (e.g. `IMS_UNREACHABLE`, `CORE_TIMEOUT`)  
- Distributes traffic across simulated towers  

### Monitor

- Aggregates calls from the last N minutes  
- Computes:
  - total calls  
  - failed calls  
  - failure rate  
  - average latency  
  - p95 latency  
  - worst-performing towers  
- Classifies the window as `OK`, `WARN`, or `ALERT`

---

## Architecture

Generator (Python) → PostgreSQL → Monitor (Python)

Key files:

- `src/generate_calls.py` – event generator  
- `src/monitor.py` – monitoring logic  
- `src/db.py` – database access  
- `db/schema.sql` – schema + indexes  
- `docker-compose.yml` – app + DB containers  

---

## Data Model

Table: `emergency_calls`

Columns:

- `call_id` (serial primary key)  
- `timestamp` (timestamptz, UTC)  
- `caller_id`  
- `tower_id`  
- `latency_ms`  
- `status` (`SUCCESS` or `FAILED`)  
- `failure_reason` (nullable)  

Indexes:

- `timestamp`
- `status`
- `tower_id`

Optimised for time-windowed aggregation queries.

---

## Running with Docker

Start services:

```bash
docker compose up --build
```

Database is exposed on:

- Host: `localhost`
- Port: `5433`

Generate traffic:

```bash
docker compose run --rm app python -m src.generate_calls --rate 5 --failure-prob 0.2 --count 200
```

Run monitoring:

```bash
docker compose run --rm app python -m src.monitor --once --window 10
```

---

## Example Output

```
[ALERT] last_10m total=200 failed=38 failure_rate=19.0% avg_latency=640ms p95=1134ms
  worst_towers:
    - TOWER_5: failure=26.83% (11/41)
```

---

## Scope

- Time-based aggregation queries  
- Reliability signal detection  
- Operational CLI tooling  
- Containerised local environment  

Backend monitoring logic only.
