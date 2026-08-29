"""CLI Script for Real GitHub Public Signal Ingestion.

Fetches live events from GitHub REST API, normalizes them, and processes them through
the IngestionService with atomic persistence and deduplication.

Usage:
    python -m scripts.ingest_github
    python scripts/ingest_github.py --limit 30 --repo fastapi/fastapi
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure backend package is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.database import init_db, AsyncSessionLocal
from app.storage.repositories import EventRepository
from app.ingestion.service import IngestionService
from app.ingestion.sources import GitHubClient, GitHubAPIException, GitHubRateLimitException


async def run_ingestion(limit: int = 30, repo: str | None = None, tenant_id: str = "demo_github") -> None:
    """Connect to GitHub REST API, fetch real events, and ingest them into Ledger."""
    await init_db()

    client = GitHubClient()

    print(f"Connecting to GitHub REST API...")
    try:
        if repo:
            owner, repo_name = repo.split("/")
            raw_events = await client.fetch_repo_events(owner, repo_name, limit=limit)
        else:
            raw_events = await client.fetch_public_events(limit=limit)
    except GitHubRateLimitException as exc:
        print(f"[ERROR] GitHub Rate Limit Exceeded: {exc}")
        sys.exit(1)
    except GitHubAPIException as exc:
        print(f"[ERROR] GitHub API Error: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"[ERROR] Unexpected Error: {exc}")
        sys.exit(1)

    fetched_count = len(raw_events)
    normalized_count = 0
    inserted_count = 0
    duplicate_count = 0
    failed_count = 0

    async with AsyncSessionLocal() as session:
        repository = EventRepository(session)
        service = IngestionService(repository=repository)

        headers = {"X-GitHub-Event": "public_event"}

        for payload in raw_events:
            try:
                event, is_duplicate = await service.process_signal(
                    headers=headers,
                    payload=payload,
                    tenant_id=tenant_id,
                )
                normalized_count += 1
                if is_duplicate:
                    duplicate_count += 1
                else:
                    inserted_count += 1
            except Exception as exc:
                failed_count += 1
                print(f"[WARN] Failed to process event: {exc}")

        await session.commit()

    print("\n" + "=" * 40)
    print(" GITHUB REAL-DATA INGESTION SUMMARY ")
    print("=" * 40)
    print(f"Fetched:    {fetched_count}")
    print(f"Normalized: {normalized_count}")
    print(f"Inserted:   {inserted_count}")
    print(f"Duplicates: {duplicate_count}")
    print(f"Failed:     {failed_count}")
    print("=" * 40)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and ingest real GitHub public signals into Ledger.")
    parser.add_argument("--limit", type=int, default=25, help="Number of GitHub events to fetch (default: 25)")
    parser.add_argument("--repo", type=str, default=None, help="Optional owner/repo format (e.g. fastapi/fastapi)")
    parser.add_argument("--tenant", type=str, default="demo_github", help="Tenant identifier (default: demo_github)")
    args = parser.parse_args()

    asyncio.run(run_ingestion(limit=args.limit, repo=args.repo, tenant_id=args.tenant))


if __name__ == "__main__":
    main()
