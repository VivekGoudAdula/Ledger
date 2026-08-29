"""Deterministic Event Fingerprinting Strategy.

Extracts normalized, stable grouping keys from canonical SignalEvents to identify incidents.
"""

import hashlib
from app.domain.models import SignalEvent


class DeterministicFingerprinter:
    """Generates reproducible, case-insensitive grouping keys for coalescing."""

    def generate_fingerprint(self, event: SignalEvent) -> str:
        """Derive stable coalesce_key from normalized event attributes.

        Normalizes tenant, source, target resource/repository, and event category,
        excluding volatile fields such as event_id or timestamp.
        """
        tenant = (event.tenant_id or "default").strip().lower()
        source = (event.source_type or "generic").strip().lower()
        
        # Extract target resource/repository/service from metadata or payload
        resource = self._extract_resource(event)
        event_category = self._extract_category(event)

        raw_key = f"{tenant}:{source}:{resource}:{event_category}"
        return raw_key

    def _extract_resource(self, event: SignalEvent) -> str:
        """Extract resource identifier (repo, service name, or system module)."""
        if event.metadata and "repository" in event.metadata:
            return str(event.metadata["repository"]).strip().lower()
        if "service" in event.raw_payload:
            return str(event.raw_payload["service"]).strip().lower()
        if "repository" in event.raw_payload:
            repo_val = event.raw_payload["repository"]
            if isinstance(repo_val, dict):
                return str(repo_val.get("full_name") or repo_val.get("name") or "unknown").strip().lower()
            return str(repo_val).strip().lower()
        return event.coalesce_key.replace("github_", "").replace("incident_", "").strip().lower()

    def _extract_category(self, event: SignalEvent) -> str:
        """Extract normalized event category."""
        event_type = (event.event_type or "").lower()
        if "issue" in event_type:
            return "issue"
        if "pull" in event_type or "pr" in event_type:
            return "pull_request"
        if "workflow" in event_type or "action" in event_type:
            return "workflow_failure"
        if "incident" in event_type or "alert" in event_type:
            return "alert"
        return "generic_event"
