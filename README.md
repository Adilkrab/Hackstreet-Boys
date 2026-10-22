# Hackstreet-Boys

---

# Inventory SME — Hackstreet Boys

Member 3's Python FastAPI + SQLAlchemy + SQLite workflow backend, arranged for
the team's shared repository. Orbyte sync is simulated. No credentials needed.

## Project structure and ownership

```text
backend/
  main.py                    # Standalone demo application
  models.py                  # Workflow request and audit models; exports Product and Base
  core.py                    # Standalone Product or Member 1 adapter
  database.py                # SQLite engine and session dependency
  schemas.py                 # Request and response contract
  seed_demo.py               # Five products and three demo scenarios
  requirements.txt
  routes/
    workflow.py              # Counts, reviews, pending queue, audit logs
    integration.py           # Simulated Orbyte sync
  services/
    inventory.py             # Product-list helper; core CRUD belongs to Member 1
    import_service.py        # Reserved for Member 1; no importer implemented
    automation.py            # Detection, transactional review, audit helpers
    integration_service.py   # Orbyte payload generation
frontend/
  src/
    components/
    pages/
    services/
  package.json               # Scaffold only; Member 2 supplies React app
sample_data/
  products.csv
tests/
  test_workflow.py
README.md
```

The GitHub repository name may stay Hackstreet-Boys: the folders above belong
at the repository root (not inside a second nested inventory-sme directory).
Keep existing teammate implementations when merging; frontend and import-service
scaffolds are only for paths that do not already exist.

## Quick start

Python 3.11+ recommended. Run all commands from the repository root:

```bash
python -m pip install -r backend/requirements.txt
python -m backend.seed_demo
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs. Run the integration suite with:

```bash
python -m pytest -q
```

Seed data is safe to rerun without resetting existing stock or repeating demo
scenarios. SQLite lives in backend/data/inventory.sqlite3, which is not committed.
Use WORKFLOW_DATABASE_URL to select another database explicitly. Store SQLite on
a persistent disk when hosting beyond a local demo.

The frontend folder is deliberately not a runnable app; Member 2 owns it.
This module does not include authentication or a production role system.

## Endpoints for Member 2

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/products` | Standalone demo product picker |
| POST | `/api/workflow/stock-count` | Submit an absolute physical count |
| GET | `/api/workflow/pending-approvals` | Pending queue with SKU, name, MYR impact and staleness |
| POST | `/api/workflow/approvals/{request_id}/review` | Approve/reject once |
| GET | `/api/workflow/audit-logs` | Chronological audit trail |
| POST | `/api/integration/orbyte-sync` | Generate and audit a simulated Orbyte payload |

Swagger `/docs`, ReDoc `/redoc`, machine-readable contract `/openapi.json`.
Use the live OpenAPI contract for frontend types. Decimal money values are JSON
**strings** (e.g. `"49.80"`) to preserve exactness.

Stock count example (use a real ID from `/api/products`):

```json
{
  "product_id": 1,
  "physical_counted_qty": 35,
  "submitted_by": "Stock clerk",
  "reason": "Damaged stock discovered during shelf count"
}
```

Review example:

```json
{
  "action": "APPROVE",
  "manager_name": "Store manager",
  "notes": "Verified against damaged-goods record"
}
```

`action` must be uppercase `APPROVE` or `REJECT`. A pending response includes
the stored before quantity, physical count, signed delta, unit-price snapshot,
financial impact, submitter, reason and timestamps. Completed reviews also
include reviewer, review notes and review time.

Audit filters: `?product_id=1&action_type=APPROVAL_GRANTED`.
Pending and audit lists support `offset=0&limit=100` (maximum 500), oldest first.
Action types: `DISCREPANCY_DETECTED`, `AUTO_ADJUSTED`, `APPROVAL_GRANTED`,
`APPROVAL_REJECTED`, `ORBYTE_SYNC`.

Sync accepts no body, `{}`, or `{"actor":"Demo integration","since":"2026-01-01T00:00:00Z"}`.
It returns approved changes since the supplied time (default last 24 hours),
current low-stock alerts (`quantity <= threshold`), MYR currency, sync log ID
and `status: "SIMULATED_SUCCESS"`. Pending/rejected changes are excluded.
It performs **no external HTTP calls** and makes **no delivery guarantees**.
Repeated syncs intentionally overlap; consumers can deduplicate by `audit_log_id`.

### Business and safety rules

- Auto-approve only if `abs(delta) <= 2` **and** `abs(delta) * unit_price < 50.00`
  **and** the physical count is nonnegative.
- Exactly RM50, more than two units, or negative counts remain pending.
- Physical counts are **absolute quantities**, not incremental adjustments.
- Negative counts are retained and audited as high-risk input per the brief;
  they cannot be approved. Reject and submit a corrected count.
- If current stock differs from the request's recorded quantity, approval returns
  **409** rather than overwriting subsequent changes. Reject and recount.
- Duplicate reviews (including reviews of auto-approved requests) return **400**.
- Missing product/request returns **404**; invalid input returns **422**.
- Each write owns a fresh session transaction. SQLite `BEGIN IMMEDIATE` serializes
  writes before reads; other SQL databases use row locks and a quantity
  compare-and-set. Audit and stock writes commit/roll back together.
- Financial impact and price are snapshotted at submission, never recomputed
  using a later product price.
- A matching physical count has zero impact and is logged as `AUTO_ADJUSTED`.

**Demo security boundary:** names supplied in JSON are attribution labels, not
verified identities. No authentication or manager authorization is included.
Before production, attach your team's authenticated-user and manager-role
dependencies, derive actors from the session, and protect the sync endpoint.
Audit logs have no edit/delete API, but are not tamper-proof against database
administrators. This is not a production security/compliance system.

### React connection

```js
const response = await fetch("/api/workflow/stock-count", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    product_id: 1, physical_counted_qty: 35,
    submitted_by: "Stock clerk", reason: "Physical count"
  })
});
const data = await response.json();
if (!response.ok) throw new Error(data.detail ?? "Request failed");
```

On a separate frontend origin, use that backend's base URL and set
`WORKFLOW_CORS_ORIGINS` to a comma-separated list of exact frontend origins.
Defaults: `http://localhost:5173,http://localhost:3000`. CORS is not authorization.

## Plug into Member 1's existing core

Do **not** create a second Product table. Before importing this package, set:

```bash
export WORKFLOW_CORE_MODULE=your_app.models
export WORKFLOW_DATABASE_URL=sqlite:////absolute/path/to/member1.sqlite3
```

That Python module must export `Base` (the shared SQLAlchemy declarative base)
and `Product` with `id`, `sku`, `name`, `system_quantity`, `unit_price`,
`low_stock_threshold`. Prices must be nonnegative, ideally `Numeric(..., 2)`.
The FK uses the actual imported `Product.id`, not a hardcoded table name.
This is an adapter hook; adapt it if Member 1 uses different field names.
Importing the workflow models registers their two tables on the shared metadata.

In Member 1's FastAPI entry point:

```python
from backend.database import get_db as workflow_get_db
from backend.routes.workflow import router as workflow_router
from backend.routes.integration import router as integration_router
from your_app.database import get_db as core_get_db

app.include_router(workflow_router)
app.include_router(integration_router)
app.dependency_overrides[workflow_get_db] = core_get_db
```

`core_get_db` must yield a **fresh synchronous SQLAlchemy Session**, without an
already-active transaction. Services own commit/rollback; don't wrap writes in
another unit of work. Use Member 1's normal migrations to create
`stock_adjustment_requests` and `audit_logs`. For a fresh hackathon SQLite DB,
import the workflow models and call `Base.metadata.create_all(engine)`.
Existing databases need proper migrations; `create_all` doesn't alter tables.

Copy `backend/` plus the dependency list into Member 1's project.
`main.py` and the standalone Product are demo-only and need not be integrated.

## Demo scenarios

Five Malaysian minimarket products: Milo 1kg, Maggi Kari 5-pack,
Buruh Cooking Oil 5kg, Jasmine Rice 10kg, Ayam Brand Sardines 425g.

1. Maggi: 80 → 79, −1 unit, RM5.80, auto-approved.
2. Milo: 40 → 35, −5 units, RM124.50, pending then manager-approved.
3. Oil: count 21 against 25, −4 units, RM123.60, manager-rejected; stock stays 25.

Sardines start below threshold to demonstrate the Orbyte low-stock payload.
To create a pending item in Swagger, count Milo as 30 after seeding.

Tests use isolated temporary SQLite files and cover the five required cases,
both risk boundaries, signed discrepancies, negatives, stale approvals, filters,
sync payloads, validation, concurrent duplicate reviews and transaction rollback.
