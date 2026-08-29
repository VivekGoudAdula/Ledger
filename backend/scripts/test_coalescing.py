"""CLI Script for Event Coalescing & Aggregation Demonstration.

Simulates 100 related signals entering the system, demonstrating coalescing into a single
CoalescedIncident while preserving all 100 original SignalEvents.

Usage:
    python -m scripts.test_coalescing
    python scripts/test_coalescing.py --count 100
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ensure backend package is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.database import init_db, AsyncSessionLocal
from app.storage.repositories import EventRepository, IncidentRepository
from app.coalescing.service import CoalescingService
from app.ingestion.service import IngestionService


async def run_coalescing_demo(count: int = 100, tenant_id: str = "demo_coalesce") -> None:
    """Run coalescing demonstration with synthetic related signals."""
    await init_db()

    print(f"Generating {count} related incident signals...")

    async with AsyncSessionLocal() as session:
        event_repo = EventRepository(session)
        incident_repo = IncidentRepository(session)
        coalescing_service = CoalescingService(repository=incident_repo, window_seconds=600)
        ingestion_service = IngestionService(
            repository=event_repo,
            coalescing_service=coalescing_service,
        )

        headers = {"X-GitHub-Event": "issues"}
        start_time = datetime.now(timezone.utc)

        # Generate `count` related events within a 2-minute sliding window
        for i in range(count):
            payload = {
                "action": "opened",
                "issue": {
                    "id": 5000 + i,  # Distinct issue ID for each event!
                    "number": 100 + i,
                    "title": f"Payment Gateway Failure Spike #{i}",
                },
                "repository": {"full_name": "org/payment-service"},
                "timestamp": (start_time + timedelta(seconds=i * 0.5)).isoformat(),
            }

            await ingestion_service.process_signal(
                headers=headers,
                payload=payload,
                tenant_id=tenant_id,
            )

        await session.commit()

        # Fetch telemetry metrics summary
        metrics = await incident_repo.get_metrics_summary(tenant_id=tenant_id)
        candidate = await incident_repo.find_candidate_incident(
            tenant_id=tenant_id,
            coalesce_key="demo_coalesce:github:org/payment-service:issue",
            window_start=start_time - timedelta(seconds=60),
        )

        # Fetch signals linked to the incident
        linked_signals = []
        if candidate:
            linked_signals = await incident_repo.get_signals_for_incident(candidate.incident_id)

    print("\n" + "=" * 50)
    print(" LEDGER COALESCING DEMONSTRATION SUMMARY ")
    print("=" * 50)
    print(f"Input Signals:              {metrics['signals_received']}")
    print(f"Coalesced Incidents Created: {metrics['incidents_created']}")
    print(f"Original Signals Preserved:  {len(linked_signals)}")
    print(f"Coalescing Ratio:           {metrics['coalescing_ratio']}x")
    print(f"Avg Signals / Incident:     {metrics['avg_signals_per_incident']}")
    if candidate:
        print(f"Representative Incident ID: {candidate.incident_id}")
        print(f"Coalescing Method:          {candidate.coalescing_method}")
        print(f"Coalesce Key:               {candidate.coalesce_key}")
    print("=" * 50)


def main() -> None:
    parser = argparse.ArgumentParser(description="Demonstrate Ledger signal coalescing.")
    parser.add_argument("--count", type=int, default=100, help="Number of signals to coalesce (default: 100)")
    parser.add_argument("--tenant", type=str, default="demo_coalesce", help="Tenant ID")
    args = parser.parse_args()

    asyncio.run(run_coalescing_demo(count=args.count, tenant_id=args.tenant))


if __name__ == "__main__":
    main()
