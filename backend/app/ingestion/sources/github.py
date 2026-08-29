"""GitHub Webhook & API Source Adapter.

Converts GitHub events (issues, PRs, workflow runs, releases) into canonical SignalEvent entities.
"""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any

from app.domain.models import SignalEvent
from app.domain.enums import SeverityLevel, EventSource
from app.ingestion.sources.base import BaseSourceAdapter


class GitHubSourceAdapter(BaseSourceAdapter):
    """Adapter for GitHub webhook and REST API signals."""

    @property
    def source_type(self) -> str:
        return EventSource.GITHUB.value

    def can_handle(self, headers: dict[str, str], payload: dict[str, Any]) -> bool:
        """Check if payload or headers indicate a GitHub signal."""
        event_header = headers.get("x-github-event") or headers.get("X-GitHub-Event")
        is_github_type = payload.get("type") in ["PushEvent", "IssuesEvent", "PullRequestEvent", "ReleaseEvent", "WorkflowRunEvent"]
        return bool(event_header or is_github_type or "repository" in payload or "issue" in payload or "pull_request" in payload)

    def parse_raw(self, headers: dict[str, str], payload: dict[str, Any], tenant_id: str) -> SignalEvent:
        """Parse raw GitHub event into canonical SignalEvent."""
        gh_type = headers.get("x-github-event") or headers.get("X-GitHub-Event") or payload.get("type") or "generic_event"
        gh_type_clean = str(gh_type).replace("Event", "").lower()
        
        # Extract source ID and details based on GitHub event schema
        repo_name = self._extract_repo_name(payload)
        source_id, event_subtype, severity, html_url = self._extract_event_details(gh_type_clean, payload)

        raw_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(raw_bytes).hexdigest()
        coalesce_key = f"github_{repo_name}_{gh_type_clean}"

        # Standard TTL for GitHub signals: 2 hours (30 min for failures)
        ttl = timedelta(minutes=30 if severity == SeverityLevel.HIGH else 120)
        deadline = datetime.now(timezone.utc) + ttl

        metadata = {
            "repository": repo_name,
            "github_event_type": gh_type_clean,
            "event_subtype": event_subtype,
            "html_url": html_url,
            "delivery_id": headers.get("x-github-delivery") or headers.get("X-GitHub-Delivery"),
        }

        return SignalEvent(
            source_type=self.source_type,
            source_id=source_id,
            tenant_id=tenant_id,
            payload_hash=payload_hash,
            coalesce_key=coalesce_key,
            event_type=f"github_{gh_type_clean}_{event_subtype}",
            severity=severity,
            raw_payload=payload,
            metadata=metadata,
            deadline_at=deadline,
        )

    def _extract_repo_name(self, payload: dict[str, Any]) -> str:
        """Extract repository full name."""
        if isinstance(payload.get("repo"), dict):
            return payload["repo"].get("name", "unknown/repo")
        if isinstance(payload.get("repository"), dict):
            return payload["repository"].get("full_name", "unknown/repo")
        return "unknown/repo"

    def _extract_event_details(self, gh_type: str, payload: dict[str, Any]) -> tuple[str, str, SeverityLevel, str | None]:
        """Extract (source_id, subtype, severity, html_url) from payload."""
        payload_id = str(payload.get("id") or "")
        
        if "issue" in payload or gh_type in ["issues", "issue"]:
            issue = payload.get("issue", payload)
            issue_id = str(issue.get("id", payload_id or "unknown"))
            number = issue.get("number", "0")
            action = payload.get("action", "opened")
            url = issue.get("html_url")
            return f"issue_{issue_id}", f"issue_{action}_{number}", SeverityLevel.MEDIUM, url

        if "pull_request" in payload or gh_type in ["pullrequest", "pull_request"]:
            pr = payload.get("pull_request", payload)
            pr_id = str(pr.get("id", payload_id or "unknown"))
            number = pr.get("number", "0")
            action = payload.get("action", "opened")
            url = pr.get("html_url")
            return f"pr_{pr_id}", f"pr_{action}_{number}", SeverityLevel.MEDIUM, url

        if "workflow_run" in payload or gh_type in ["workflow_run", "workflowrun"]:
            wf = payload.get("workflow_run", payload)
            wf_id = str(wf.get("id", payload_id or "unknown"))
            conclusion = wf.get("conclusion") or payload.get("action", "run")
            severity = SeverityLevel.HIGH if conclusion == "failure" else SeverityLevel.MEDIUM
            url = wf.get("html_url")
            return f"workflow_{wf_id}", f"workflow_{conclusion}", severity, url

        if "release" in payload or gh_type in ["release"]:
            rel = payload.get("release", payload)
            rel_id = str(rel.get("id", payload_id or "unknown"))
            tag = rel.get("tag_name", "v0")
            url = rel.get("html_url")
            return f"release_{rel_id}", f"release_{tag}", SeverityLevel.MEDIUM, url

        # Fallback for push or general event
        source_id = payload_id or f"gh_{hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]}"
        return source_id, gh_type, SeverityLevel.INFO, None
