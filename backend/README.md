# Ledger — Value-Aware Admission Control Platform

> **System Statement:**  
> *"Signal Labs decides what deserves attention. Ledger decides what deserves compute."*

Ledger is a production-minded, modular, distributed systems project for the Signal Labs AI HackDay.

---

## Phase 1 Implementation — Canonical Event Contract + Real Signal Ingestion

Phase 1 establishes the canonical event contract, pluggable source adapters, deterministic normalization, database deduplication, and real public GitHub signal ingestion.

### 1. Canonical `SignalEvent` Contract

The canonical `SignalEvent` entity is source-independent and immutable:

```python
SignalEvent(
    event_id: str,             # Non-empty unique UUID or stable source ID
    source_type: str,          # e.g., 'github', 'incident', 'generic_api'
    source_id: str,            # Source identifier
    tenant_id: str,            # Multi-tenant identifier
    event_type: str,           # Normalized subtype (e.g. 'github_issues_opened_42')
    severity: SeverityLevel,   # Enum: CRITICAL, HIGH, MEDIUM, LOW, INFO
    payload_hash: str,         # SHA-256 fingerprint of raw payload
    coalesce_key: str,         # Grouping key for semantic coalescing
    raw_payload: dict,         # Source JSON
    metadata: dict,            # Repository, delivery_id, html_url metadata
    created_at: datetime,      # Timezone-aware UTC timestamp
    deadline_at: datetime,     # Timezone-aware TTL deadline
    status: EventStatus        # State machine enum (e.g. NORMALIZED)
)
```

---

## 2. Ingestion Data Flow

```
Real Signal Source (GitHub Public API / Webhook)
       ↓
Source Adapter (GitHubSourceAdapter / IncidentSourceAdapter)
       ↓
Deterministic Normalizer (EventNormalizer)
       ↓
Canonical SignalEvent (Validation & Timezone Enforcement)
       ↓
Ingestion Application Service (IngestionService)
       ↓
Repository Layer (EventRepository with SQLite WAL Unique Constraint)
       ↓
Queryable Database Record
```

---

## 3. Environment Setup & Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Install dependencies:

```bash
pip install -e .[dev]
```

---

## 4. Running the Ingestion API

Start the FastAPI application server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Health Check:** `GET http://localhost:8000/health`
- **Ingest Signal:** `POST http://localhost:8000/signals`

---

## 5. Manual Real-Data GitHub Ingestion CLI

Fetch and ingest live public events directly from the official GitHub REST API:

```bash
python -m scripts.ingest_github --limit 25
```

Fetch events for a specific repository:

```bash
python -m scripts.ingest_github --limit 30 --repo fastapi/fastapi
```

Example CLI Output:

```
Connecting to GitHub REST API...

========================================
 GITHUB REAL-DATA INGESTION SUMMARY 
========================================
Fetched:    25
Normalized: 25
Inserted:   23
Duplicates: 2
Failed:     0
========================================
```

---

## 6. Running the Automated Test Suite

Execute unit and integration tests with pytest:

```bash
python -m pytest -o pythonpath=. -v
```

---

## 7. Known Limitations (Phase 1 Scope)

Phase 1 strictly covers ingestion, normalization, canonical event contracts, and deduplication storage.
Future phases will introduce semantic coalescing windows, LLM value estimation, deterministic admission control, transactional queue worker pools, and observability dashboards.
