import argparse
import random
import time
from datetime import datetime, timezone

from faker import Faker

from src.db import insert_emergency_call

fake = Faker()


FAILURE_REASONS = [
    "CORE_TIMEOUT",
    "IMS_UNREACHABLE",
    "AUTH_FAILURE",
    "ROUTING_ERROR",
    "PSAP_UNREACHABLE",
]


def generate_call_event(failure_prob: float, tower_count: int) -> dict:
    """
    Creates one synthetic emergency call record.
    """
    latency_ms = random.randint(40, 1200)

    is_failed = random.random() < failure_prob
    status = "FAILED" if is_failed else "SUCCESS"
    failure_reason = random.choice(FAILURE_REASONS) if is_failed else None

    return {
        "timestamp": datetime.now(timezone.utc),  # store UTC
        "caller_id": fake.msisdn()[:15],  # phone-like id, capped
        "tower_id": f"TOWER_{random.randint(1, tower_count)}",
        "latency_ms": latency_ms,
        "status": status,
        "failure_reason": failure_reason,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic emergency call events.")
    parser.add_argument("--rate", type=float, default=2.0, help="Events per second (default: 2)")
    parser.add_argument("--failure-prob", type=float, default=0.05, help="Failure probability (default: 0.05)")
    parser.add_argument("--towers", type=int, default=10, help="Number of towers (default: 10)")
    parser.add_argument("--count", type=int, default=0, help="If >0, generate exactly N events then exit.")
    args = parser.parse_args()

    interval = 1.0 / max(args.rate, 0.01)

    i = 0
    while True:
        event = generate_call_event(args.failure_prob, args.towers)
        call_id = insert_emergency_call(event)

        print(
            f"[{event['timestamp'].isoformat()}] call_id={call_id} "
            f"tower={event['tower_id']} status={event['status']} latency_ms={event['latency_ms']}"
            + (f" reason={event['failure_reason']}" if event["failure_reason"] else "")
        )

        i += 1
        if args.count and i >= args.count:
            break

        time.sleep(interval)


if __name__ == "__main__":
    main()