# Hackstreet-Boys

---

# Inventory SME — Hackstreet Boys

Python FastAPI + SQLAlchemy + SQLite inventory backend with product management,
stock movement history, CSV/XLSX imports and Member 3's approval workflow.
Orbyte sync is simulated. No credentials needed for the local demo.

## Project structure and ownership

```text
backend/
  main.py                    # Shared API application
  models.py                  # Stock movement, workflow request and audit models
  core.py                    # Shared Product and Base; optional external adapter
  database.py                # SQLite engine and session dependency
  schema_setup.py            # Table creation and original SQLite audit upgrade
  schemas.py                 # Request and response contract
  seed_demo.py               # Five products and three demo scenarios
  requirements.txt
  routes/
    inventory.py             # Products, movements, low-stock alerts, uploads
    workflow.py              # Counts, reviews, pending queue, audit logs
    integration.py           # Simulated Orbyte sync
  services/
    inventory.py             # Product operations and shared stock-changing function
    import_service.py        # CSV/XLSX validation, preview and atomic import
    common.py                # Shared transactions and audit helper
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
| GET | `/api/products/{product_id}` | Retrieve one product |
| POST | `/api/products` | Add a product and opening stock |
| PATCH | `/api/products/{product_id}` | Edit product details, excluding stock quantity |
| POST | `/api/stock-movements` | Record normal stock-in or stock-out |
| GET | `/api/stock-movements` | Movement history, optionally filtered by product |
| GET | `/api/alerts` | Current low-stock products |
| POST | `/api/inventory/import` | Preview or commit a CSV/XLSX upload |
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
Product, movement, alert, pending and audit lists support `offset=0&limit=100` (maximum 500).
Movement, pending and audit lists are oldest first.
Action types: `DISCREPANCY_DETECTED`, `AUTO_ADJUSTED`, `APPROVAL_GRANTED`,
`APPROVAL_REJECTED`, `ORBYTE_SYNC`, `PRODUCT_CREATED`, `PRODUCT_UPDATED`,
`STOCK_IN`, `STOCK_OUT`, `INVENTORY_IMPORTED`.

Sync accepts no body, `{}`, or `{"actor":"Demo integration","since":"2026-01-01T00:00:00Z"}`.
It returns approved adjustments and normal stock-in/out changes since the supplied time (default last 24 hours),
current low-stock alerts (`quantity <= threshold`), MYR currency, sync log ID
and `status: "SIMULATED_SUCCESS"`. Pending/rejected changes are excluded.
It performs **no external HTTP calls** and makes **no delivery guarantees**.
Repeated syncs intentionally overlap; consumers can deduplicate by `audit_log_id`.
For normal stock movements, `request_id` is null. Opening stock from product
creation/import is a starting baseline and is not included in the sync change list.

### Product and stock APIs

Create a product using the existing shared field names:

```json
{"sku":"MY-TEA-500G","name":"Tea 500g","system_quantity":10,"unit_price":"12.50","low_stock_threshold":3}
```

Product creation and editing accept an optional `?actor=Clerk` query parameter
(default `Inventory staff`). SKUs are case-sensitive and unique. Duplicate SKUs
return 409. Prices must be nonnegative with at most two decimal places; quantities
must be whole numbers between 0 and 2,000,000,000.

Use PATCH to edit `sku`, `name`, `unit_price`, or `low_stock_threshold`.
Quantity changes must go through stock movements or the existing count workflow.
Product deletion is not exposed, preserving movement/audit references.

Record a receipt or sale with POST `/api/stock-movements`:

```json
{"product_id":1,"movement_type":"OUT","quantity":3,"actor":"Clerk","reason":"Customer sale"}
```

`movement_type` is `IN` or `OUT`; `quantity` must be a positive integer.
Insufficient stock returns 409 and saves no movement or audit event.
GET `/api/stock-movements?product_id=1` returns signed `delta`, before/after
quantities, actor, reason, timestamp and any linked adjustment request.
History includes nonzero opening stock and approved count adjustments.
Pending/rejected counts and unchanged quantities create no stock movements.
Legacy adjustments that predate this implementation remain in the audit trail;
they are not backfilled into the new stock movement table.

### CSV / Excel imports

Send multipart form data to `/api/inventory/import`: `file`, `actor`, `dry_run`.
`dry_run=true` is the default: it validates without saving. The response includes
`valid`, `total_rows`, parsed `preview`, and `errors` with spreadsheet row numbers.
Submit the same file with `dry_run=false` to save. The server revalidates it;
all rows succeed together or nothing is saved. An invalid commit returns 422
with the validation report in `detail`.

Required headers, in any order:

```csv
sku,name,system_quantity,unit_price,low_stock_threshold
MY-TEA-500G,Tea 500g,10,12.50,3
```

Imports create new products only. Existing SKUs and duplicate SKUs within the
file are rejected; imports never silently overwrite live quantities. Use the
stock movement or count APIs for existing stock.

Supported formats: UTF-8 CSV (optional BOM) and the first worksheet of `.xlsx`.
Maximum upload: 5 MiB, 2,000 data rows; maximum expanded XLSX: 25 MiB.
Formula cells and legacy `.xls` files are rejected. Use values and export as XLSX/CSV.
The existing `sample_data/products.csv` is suitable for an empty database;
after seeding, its SKUs already exist and importing it will be rejected.

### Existing demo database

Startup and the demo seed automatically add the new tables and upgrade the
original SQLite audit-event constraint, retaining products and audit records.
The upgrade is transactional and safe to rerun. It only recognizes the original
audit schema; customized schemas and non-SQLite databases require an explicit
migration. Keep a database backup when upgrading any populated deployment.

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
`stock_adjustment_requests`, `audit_logs`, and `stock_movements`. For a fresh hackathon SQLite DB,
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
