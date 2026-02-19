"""Mock data generators for CRM, Support, and Analytics data sources.

These generators can be used to regenerate the sample JSON files in data/ or
to produce fresh in-memory datasets for testing.

Usage:
    python -m app.utils.mock_data          # regenerate data/*.json
"""

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
NUM_CUSTOMERS = 50
NUM_TICKETS = 50
ANALYTICS_DAYS = 30
ANALYTICS_METRICS = ["daily_active_users", "page_views", "api_calls", "error_rate", "avg_response_time_ms"]

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def generate_customers(count: int = NUM_CUSTOMERS) -> List[Dict[str, Any]]:
    """Generate realistic CRM customer records."""
    statuses = ["active", "inactive"]
    now = datetime.now(timezone.utc)
    customers: List[Dict[str, Any]] = []
    for i in range(1, count + 1):
        created = now - timedelta(days=random.randint(1, 365))
        customers.append({
            "customer_id": i,
            "name": f"Customer {i}",
            "email": f"user{i}@example.com",
            "created_at": created.isoformat(),
            "status": random.choice(statuses),
        })
    return customers


def generate_support_tickets(count: int = NUM_TICKETS, max_customer_id: int = NUM_CUSTOMERS) -> List[Dict[str, Any]]:
    """Generate realistic support ticket records."""
    priorities = ["low", "medium", "high"]
    statuses = ["open", "closed"]
    now = datetime.now(timezone.utc)
    tickets: List[Dict[str, Any]] = []
    for i in range(1, count + 1):
        created = now - timedelta(days=random.randint(0, 30))
        tickets.append({
            "ticket_id": i,
            "customer_id": random.randint(1, max_customer_id),
            "subject": f"Issue {i}",
            "priority": random.choice(priorities),
            "created_at": created.isoformat(),
            "status": random.choice(statuses),
        })
    return tickets


def generate_analytics(days: int = ANALYTICS_DAYS, metrics: List[str] | None = None) -> List[Dict[str, Any]]:
    """Generate time-series analytics/metrics data."""
    if metrics is None:
        metrics = ANALYTICS_METRICS
    now = datetime.now(timezone.utc).date()
    records: List[Dict[str, Any]] = []
    for metric in metrics:
        for d in range(days):
            date = now - timedelta(days=d)
            if metric == "error_rate":
                value = round(random.uniform(0.1, 5.0), 2)
            elif metric == "avg_response_time_ms":
                value = random.randint(50, 500)
            else:
                value = random.randint(100, 1000)
            records.append({
                "metric": metric,
                "date": date.isoformat(),
                "value": value,
            })
    return records


def write_json(filepath: Path, data: List[Dict[str, Any]]) -> None:
    """Write a list of records to a JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def regenerate_all() -> None:
    """Regenerate all sample data files in data/ directory."""
    write_json(DATA_DIR / "customers.json", generate_customers())
    write_json(DATA_DIR / "support_tickets.json", generate_support_tickets())
    write_json(DATA_DIR / "analytics.json", generate_analytics())
    print(f"Regenerated mock data in {DATA_DIR}")


if __name__ == "__main__":
    regenerate_all()
