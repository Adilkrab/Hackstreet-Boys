# Frontend (Member 2): StokSemak

React + Vite screens for the SME inventory count and approval workflow.
The app talks only to the FastAPI backend in `../backend`.

## Run it locally

You need two terminals, both started from the **repository root**.

Terminal 1, backend:

```bash
python -m pip install -r backend/requirements.txt
python -m backend.seed_demo
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Terminal 2, frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite forwards every `/api/...` request to
`http://localhost:8000`, so no CORS setup is needed. To use another backend
address, start the frontend with `BACKEND_URL=http://host:port npm run dev`, or
set `VITE_API_URL` when the frontend is hosted separately from the backend.

## Screens and where they live

| Screen | File | Journey step |
|---|---|---|
| Dashboard: approvals waiting, low-stock warnings, recent activity, Orbyte sync | `src/pages/Dashboard.jsx` | Overview |
| Products: table, search, stock in/out, history, add product, CSV/XLSX import | `src/pages/Products.jsx` | Connected data |
| Stock count: live "what will happen" explanation before submitting | `src/pages/StockCount.jsx` | Trigger + decision |
| Approvals: approve/reject with notes; stale and negative counts blocked | `src/pages/Approvals.jsx` | Human approval |
| Activity log: plain-English audit trail, filters, CSV export | `src/pages/ActivityLog.jsx` | Visible outcome |

Other files:

- `src/services/api.js`: every backend call in one place
- `src/config.js`: app name, demo shop, demo users and roles, auto-fix thresholds
- `src/utils/activity.js`: turns audit entries into readable sentences
- `src/components/`: shared UI pieces

## Roles (simulated login)

Use the **Owner / Stock clerk** switch at the top right. The Domain 2 brief
allows login and RBAC to be simulated.

- **Stock clerk** can record stock in/out and submit counts, and can *see*
  approvals but cannot approve them.
- **Owner** can also approve or reject, add products and import spreadsheets.

The selected name is sent to the backend as the actor, so it appears in the
activity log.

## 3-minute demo script

1. Switch to **Stock clerk**. Go to **Stock count**, pick Maggi, count 1 less
   than the system shows, and submit. It is **fixed automatically** and logged.
2. Count **Milo** 7 less than the system shows. The preview explains why it
   **needs owner approval**. Submit.
3. Open **Approvals**. As a clerk, the buttons are locked.
4. Switch to **Owner**, add a note and **Approve**. The stock updates.
5. Open the **Activity log** to show the full trail: who did what, and when.
6. On the **Dashboard**, press **Sync to Orbyte now** to show the payload that
   would go to the Orbyte hub.

## Build for deployment

```bash
npm run build      # creates frontend/dist
npm run preview    # serves dist on port 5173, still forwarding /api
```
