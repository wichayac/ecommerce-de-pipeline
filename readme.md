# E-Commerce Orders ELT Pipeline

## Project Goal

Build a production-minded, end-to-end **ELT data pipeline** for e-commerce order data. The goal is to demonstrate core Data Engineering fundamentals—raw ingestion, data quality validation, local analytical warehousing, incremental SQL modeling, idempotency, and automated testing—without over-engineering the infrastructure.

---

## Progress & Roadmap

### Completed
- [x] **Milestone 0 — Project Setup:** Repository structure, virtual environment, `.gitignore`, `.env.example`, and `requirements.txt`.
- [x] **Milestone 1 — Extract (Raw Layer):** Built `src/pipelines/extract_orders.py` to pull order/cart data from a REST API into Hive-partitioned JSONL files (`dt=YYYY-MM-DD`) with strict date validation, request timeouts, and fail-fast HTTP error handling.
- [x]  **Milestone 2 — Validate (Data Quality Gate):** Build `src/pipelines/validate_orders.py` to enforce the raw data contract (non-empty files, valid JSON, required fields, unique IDs, numeric range checks) and output a structured `validation_report.json`.
### Next Steps
- [ ] **Milestone 3 — Load Raw (ELT):** Load validated raw JSONL partitions into a local **DuckDB** warehouse.
- [ ] **Milestone 4 — Transform (Incremental SQL):** Implement watermark-based incremental loading, `ROW_NUMBER()` deduplication, nested product flattening, and partition-safe daily summary tables.
- [ ] **Milestone 5 — Productionize & Test:** Add structured logging, retry logic, unit tests with `pytest`, and document engineering trade-offs.
- [ ] **Milestone 6 — Orchestration (Bonus):** Connect all stages via a unified CLI runner (`src/main.py`) or an Airflow DAG.

---

## Problem Statement

- **Source data:** E-commerce order/cart records exposed via REST API (`https://dummyjson.com/carts`).
- **Problem with ad-hoc ingestion:** Pulling API data directly into analytics tables without raw storage, schema validation, or idempotency causes duplicated rows on reruns, silent failures on upstream errors, and makes backfilling historical data difficult.
- **Downstream use case:** Daily order volume, item-level sales breakdown, and revenue reporting for analytics teams.
- **Target freshness:** Daily batch run partitioned by run date (`YYYY-MM-DD`).

---

## Architecture

```text
Source API -> Raw Layer (JSONL) -> Validation Gate -> DuckDB Raw Table -> Incremental SQL -> Serving Layer
```

| Step | Description | Tool | Status |
| :--- | :--- | :--- | :--- |
| **Extract** | Fetch order payloads from REST API with timeout and HTTP checks | Python (`requests`) | Done |
| **Raw Storage** | Save immutable records in date-partitioned JSON Lines files | Local JSONL (`dt=YYYY-MM-DD`) | Done |
| **Validate** | Enforce schema, null, uniqueness, and business rules; output report | Python (`json`) | Next |
| **Load Raw** | Ingest validated raw partitions into analytical storage | DuckDB | Planned |
| **Transform** | Incremental load using watermark, deduplication, and daily aggregation | SQL (DuckDB) | Planned |
| **Test** | Automated unit tests for validation rules and transformations | `pytest` | Planned |

---

## Data Contract (Raw Orders)

| Field | Type | Required | Rule |
| :--- | :--- | :--- | :--- |
| `id` | integer | yes | Primary key; must be unique per partition |
| `userId` | integer | yes | Non-null customer identifier |
| `total` | float / int | yes | Must be non-negative (`>= 0`) |
| `products` | list | yes | Must contain at least 1 product item |

**Metadata:**
- **Grain:** 1 row = 1 cart/order (`id`), containing nested `products` line items.
- **Primary key:** `id`
- **Partition column:** `dt` (run date in `YYYY-MM-DD` format)
- **Refresh frequency:** Daily batch

---

## Setup

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create local environment file
cp .env.example .env
```

---

## Run

Extract raw order records for a specific partition date:

```bash
python src/pipelines/extract_orders.py --run-date 2026-11-12
```

**Expected Output:**
`data/raw/orders/dt=2026-11-12/orders.jsonl` (one JSON object per line).

---

## Validation Output Examples

**Passed (`validation_report.json`):**
```json
{
  "run_date": "2026-11-22",
  "input_path": "data/raw/orders/dt=2026-11-22/orders.jsonl",
  "total_rows": 50,
  "error_count": 0,
  "status": "PASSED",
  "errors": []
}
```

**Failed (Sabotage Test — 5 Contract Violations Caught):**
```json
{
  "run_date": "2026-11-22",
  "input_path": "data/raw/orders/dt=2026-11-22/orders.jsonl",
  "total_rows": 50,
  "error_count": 5,
  "status": "FAILED",
  "errors": [
    "Line 1: missing or null field 'id'",
    "Line 2: invalid total -139.93",
    "Line 3: products must be a non-empty list",
    "Line 5: duplicate id 4",
    "Line 6: Invalid JSON format"
  ]
}
```

## Reliability & Engineering Decisions

### Implemented (Milestone 1)
- **Idempotency (Extract Layer):** Writes to a date-specific Hive-style partition (`dt=YYYY-MM-DD/orders.jsonl`) using overwrite mode (`"w"`). Rerunning the same date cleanly replaces that day's file without duplicating records or affecting other dates.
- **Fail-Fast Error Handling:** Validates `--run-date` ISO format via `argparse` before making network calls, enforces explicit HTTP timeouts, calls `response.raise_for_status()` before JSON parsing, and re-raises exceptions so failures never pass silently.
- **Raw Layer Replayability (ELT):** Persists raw API payloads as JSON Lines (`.jsonl`) before transformation so downstream logic can be updated and re-run without re-querying the source API.

### Planned (Upcoming Milestones)
- **Data Quality Circuit Breaker:** Halt downstream loading on contract violations while saving an audit report (`validation_report.json`).
- **Incremental Watermark & Deduplication:** Use `ROW_NUMBER()` over primary keys and partition-scoped rebuilds to handle late-arriving data safely.
- **Retry & Backoff:** Handle transient API timeouts and HTTP `5xx` errors cleanly.

---

## Project Structure

```text
.
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
└── src/
    └── pipelines/
        └── extract_orders.py
```
*(Folders `sql/`, `tests/`, and `data/` will be populated in Milestones 2–5; `data/` and `.env` are excluded via `.gitignore`.)*