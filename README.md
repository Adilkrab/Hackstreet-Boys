# Stock Manager

Inventory management for Malaysian micro and small businesses: connect spreadsheet
inputs with stock movements, physical counts, owner approvals and an activity trail.

The repository contains the Phase 1 prototype, branch-specific run instructions,
submission documents and pitch deck. The public Replit deployment is live, while
the Replit proof-of-use form still requires evidence from the team's account.

## Team Information

| Field | Details |
| --- | --- |
| **Team Name** | Hackstreet Boys |
| **Team Domain** | Domain 2: Orbyte Smart SME Challenge |
| **SDG Track (1-17)** | SDG 8: Decent Work and Economic Growth |
| **Team Leader** | Josiah Chong Ren Shun |
| **University** | Xiamen University Malaysia; Monash University Malaysia |
| **Number of Members** | 3 |

## Links

| Resource | Link / status |
| --- | --- |
| GitHub Repository | [Adilkrab/Hackstreet-Boys](https://github.com/Adilkrab/Hackstreet-Boys) |
| Submission Branch | [submission/template-layout](https://github.com/Adilkrab/Hackstreet-Boys/tree/submission/template-layout) |
| Replit Project | [SME Inventory Workflow Backend](https://replit.com/@lauleong3/SME-Inventory-Workflow-Backend) |
| Live Demo | [Stock Manager on Replit](https://hackstreetboys-stock.replit.app/stock_manager/) — deployment URL recorded in this branch |
| RunPod Endpoint | Not applicable - RunPod is not used; no GPU workload. |
| Slide Deck | [Stock Manager pitch deck](https://github.com/Adilkrab/Hackstreet-Boys/blob/main/submission/SDC2026_HackstreetBoys_Stock_Manager_Pitch.pptx) |
| Demo Video | [Link](https://youtu.be/it1FCoYTTMs?si=tLobxygI_EipJZAt) |

## Overview

### Problem

Malaysian micro and small businesses often track stock through spreadsheets,
paper records and manual follow-up. Differences between recorded quantities and
physical counts can be missed or corrected without a clear approval trail.

The proposal cites public inventory-accuracy, retail-shrink and Malaysian MSME
benchmarks and maps the project to UN SDG Targets 8.2 and 8.3.

### Solution

Stock Manager combines inventory records, validated spreadsheet imports and a
physical-count workflow. Small discrepancies can be corrected automatically;
larger discrepancies wait for an owner decision. Actions are recorded in an audit log.

Current automation is rule-based, not model inference. Orbyte sync is simulated
and sends no external requests. Owner/clerk switching is a demo simulation,
not authenticated access control. This is the declared Phase 1 scope for the
Domain 2 challenge.

### Key Features

- Product creation, stock-in/out, low-stock alerts and movement history.
- CSV/XLSX imports with a preview, validation and all-or-nothing creation of new SKUs.
- Physical stock counts with discrepancy and MYR-impact calculations.
- Automatic correction only when the difference is at most 2 units, the value is
  below RM50, and the count is nonnegative.
- Owner approval/rejection, stale-count protection and a chronological activity log.
- React dashboard, simulated roles, CSV activity export and simulated Orbyte payloads.

### Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React + Vite |
| Backend | Python + FastAPI |
| Database | SQLAlchemy + SQLite |
| Spreadsheet processing | Python CSV + openpyxl (XLSX) |
| AI / Compute | CPU-only rule-based automation; no GPU integration implemented |
| Hosting / Development | Replit Core for the combined public FastAPI and React deployment |
| Development assistance | Replit Agent, Claude, and Codex / ChatGPT; team-reviewed assistance, not runtime AI |

## Project Structure

```text
.
├── docs/
│   ├── API.md                         # Detailed API and workflow reference
│   └── architecture.md                # System flow and deployment architecture
├── src/
│   ├── __init__.py
│   ├── main.py                        # Combined app entry point
│   ├── utils.py                       # Shared application paths
│   ├── backend/                       # FastAPI, database, routes and services
│   ├── frontend/                      # React app and Vite configuration
│   └── sample_data/products.csv        # Synthetic demo inventory
├── submission/
│   ├── README.md                      # Submission contents and remaining evidence
│   ├── SDC2026_HackstreetBoys_Preliminary.pdf
│   ├── SDC2026_HackstreetBoys_TechDeclaration.pdf
│   ├── SDC2026_HackstreetBoys_Replit_POU.pdf
│   └── Stock_Manager_Pitch_Submission.pptx
├── tests/
├── .env.example
├── .gitignore
├── .replit
├── LICENSE
├── pytest.ini
├── requirements.txt
└── README.md
```

All application source is under `src/`. Tests and submission/deployment resources
stay in the root folders used by the official template. Retain the current
backend/frontend modules; there is no need to copy the template's example app.

### Architecture

```text
Browser -> React interface -> FastAPI /api routes -> SQLAlchemy -> SQLite
                                 |
                                 +-> Approval rules, movement history and audit logs
                                 +-> Simulated Orbyte payload (no external delivery)
```

For the combined app, FastAPI serves the built frontend and API on the same port.
The same flow is shown as a Mermaid diagram in [docs/architecture.md](docs/architecture.md).

## How to Run

Requirements: Git, Python 3.11+ and Node.js 20+. There are no mandatory API
credentials for the current demo.

### Option 1 - Run on Replit

1. Open the [team’s Replit project](https://replit.com/@lauleong3/SME-Inventory-Workflow-Backend), or import
   `https://github.com/Adilkrab/Hackstreet-Boys` into a new Replit project.
   These instructions describe the submission branch; for a fresh import, select
   `submission/template-layout` before running the commands below. The existing
   hosted project has its own hosting adapters and run configuration.
2. In the Replit Shell, install dependencies and optionally add the demo data:

   ```sh
   python -m pip install -r requirements.txt
   npm --prefix src/frontend ci
   python -m src.backend.seed_demo
   ```

3. Click **Run**. `.replit` builds the React app and starts `python src/main.py`.
   Open the web preview on port 8000. For publishing, the configuration provides
   separate build and run commands.
4. If configuration is needed, set variables from `.env.example` in Replit Secrets.
   `PORT` defaults to 8000. No real secret belongs in Git.
5. Open the published application using the Live Demo link above.

SQLite is local-file storage. Choose persistent storage/hosting for a deployment
that must retain changes across restarts or republishes; do not assume an
ephemeral or multi-instance deployment will preserve this database.

### Option 2 - Run locally (combined frontend + backend)

Clone the repository, then create and activate a virtual environment:

```sh
git clone --branch submission/template-layout --single-branch https://github.com/Adilkrab/Hackstreet-Boys.git
cd Hackstreet-Boys
python -m venv .venv
```

If you already have a checkout, ensure you are on `submission/template-layout`
before using these paths. Preserve any uncommitted changes before switching branches.

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```sh
source .venv/bin/activate
```

Then install, build and run:

```sh
python -m pip install -r requirements.txt
npm --prefix src/frontend ci
npm --prefix src/frontend run build
python -m src.backend.seed_demo
python src/main.py
```

Open http://localhost:8000 for the app and http://localhost:8000/docs for the API docs.
Press Ctrl+C to stop. The seed command is optional and safe to rerun without
resetting existing stock. The default database is
`src/backend/data/inventory.sqlite3` and is excluded from Git.

If PowerShell blocks activation, call `.\.venv\Scripts\python.exe` in place of
`python` in the commands above; activation is not required.

### Frontend development (two terminals)

Backend, from the repository root:

```sh
python -m uvicorn src.backend.main:app --host 0.0.0.0 --port 8000
```

Frontend, in a second terminal:

```sh
npm --prefix src/frontend run dev
```

Open http://localhost:5173. Vite proxies `/api` to the backend. Set `BACKEND_URL`
when using another backend address. `VITE_API_URL` is for a separately hosted API.
`.env.example` is a configuration reference; this Python app does not automatically
read `.env` files. Export settings in the shell or use Replit Secrets.

### Run Tests

```sh
python -m pytest -q
npm --prefix src/frontend run build
```

The Python suite uses isolated temporary databases. See [docs/API.md](docs/API.md)
for endpoints, input examples, import columns and approval behavior.

## How We Use Replit (Required)

- **AI-assisted development:** Replit Agent helped with the FastAPI/SQLAlchemy/SQLite
  workflow, stock-count and approval logic, audit logging, simulated Orbyte sync,
  testing/debugging, and deployment setup. The technical declaration records
  moderate use; the exact Agent version was not recorded.

- Development: the repository is configured so Replit installs Python and Node
  dependencies, builds the React frontend, and starts the combined FastAPI app.
- Hosting: Replit Core hosts the combined application at the public Live Demo link.
- Storage: the Phase 1 demo uses a local SQLite file and synthetic seed data.
- Secrets: the prototype requires no API keys or passwords.
- Proof of use: (https://github.com/Adilkrab/Hackstreet-Boys/blob/main/submission/SDC2026_HackstreetBoys_Replit_POU.pdf)

## How We Use RunPod (Template Requirement)

**Not used in Phase 1.** The application runs on CPU and has no model training,
fine-tuning or GPU inference. There is no RunPod endpoint, handler, API credential
requirement, or RunPod proof-of-use file in this branch. The proposal and technical
declaration disclose this scope.

The supplied submission template labels RunPod usage and proof of use as required.
The team must confirm with the organizers whether a non-GPU Domain 2 submission
is acceptable; this README does not claim an exemption or completed RunPod use.

### Prototype limitations

- Owner/clerk switching and entered names are not authentication; server-side
  authorization is still required before real use.
- SQLite is a local demo database, not a durable multi-instance production setup.
- Orbyte sync logs a JSON payload but does not deliver it to an external service.
- Counts are absolute quantities. Negative counts cannot be approved, repeated
  reviews are rejected, and approvals are blocked when stock changed after counting.
- The seed script adds missing demo products/scenarios; it does **not** wipe or
  reset existing stock. Use synthetic data only in the public demo.

## Challenges & Learnings

- Keeping frontend and backend expectations aligned required a shared API contract;
  the team used FastAPI's OpenAPI documentation and end-to-end walkthroughs.
- Import preview, pagination, CSV export and readable error handling were corrected
  after integration testing with the production frontend build.
- The team learned that inventory corrections need stale-count protection,
  transaction boundaries and clear audit records, even in a small prototype.

## Future Improvements

- Add authenticated staff accounts and server-side role authorization.
- Move production data to durable managed storage and define a retention policy.
- Connect the simulated Orbyte payload to an approved external integration.
- Pilot with 3 to 5 shop owners, measure the baseline, and validate the thresholds.
- Add advisory loss-pattern detection and bilingual summaries after the rules-based
  workflow has been validated.

### Phase 2 impact targets

The proposal maps the project to **SDG 8**, particularly Targets **8.2** and **8.3**.
The pilot will measure inventory-record accuracy, audit coverage, and owner review
workload. After measuring a baseline across 5–20 products, the team targets a 20%
relative reduction in mismatches after two count cycles, 100% of adjustments with
an audit entry and named approver or recorded rule, and a test of whether owner
reviews can be reduced by at least 50%. These are proposed targets, not measured
results.

## Team

| Name | Role | GitHub |
| --- | --- | --- |
| Josiah Chong Ren Shun (team leader) | Backend, database and imports | [Decartes159](https://github.com/Decartes159) |
| Carlson Soo | Frontend and user experience | [carlsonsoo](https://github.com/carlsonsoo) |
| Adilkrab | Automation and approval workflow | [Adilkrab](https://github.com/Adilkrab) |

## Submission Checklist

- [x] Confirm team name, domain, SDG track, leader, university and member details.
- [x] Add the final public YouTube demo-video URL.
- [x] Add and verify the public Replit live-demo URL.
- [x] Add the team’s Replit project URL.
- [x] Add the repository and pitch deck links.
- [x] Complete the preliminary document and technical/tools declaration.
- [x] Refresh the repository technical-declaration PDF from the latest document so it includes Replit Agent.
- [x] Complete Replit proof of use with evidence from the team's account.
- [x] Record "RunPod not used — no GPU workload" in the technical declaration.
- [ ] Obtain organizer confirmation on the template’s RunPod usage/proof requirement.
- [x] Rename the completed preliminary and technical forms with the registered team name.
- [x] Re-run the documented startup, tests, build, and public-demo checks on the final submission revision.
- [x] Include the final code in the submission branch; the repository is public.
- [x] Check that every submitted link works without a personal login.
- [x] Recheck the final tracked files for API keys, passwords and other credentials.
- [x] Submit through sdchack.my before the deadline and follow the repository freeze rules.

## Submission Documents & Templates

| Document | Repository copy | 
| --- | --- | 
| Preliminary proposal | [PDF](https://github.com/Adilkrab/Hackstreet-Boys/blob/main/submission/SDC2026_HackstreetBoys_Preliminary.pdf) | 
| Technical & tools declaration | [PDF](https://github.com/Adilkrab/Hackstreet-Boys/blob/main/submission/SDC%20Hackathon_%20Technical%20Tools%20Declaration%20Template.pdf) | 
| Replit proof of use | [Prood of Use](https://github.com/Adilkrab/Hackstreet-Boys/blob/main/submission/SDC2026_HackstreetBoys_Replit_POU.pdf) | 
| Pitch deck | [PowerPoint](https://github.com/Adilkrab/Hackstreet-Boys/blob/main/submission/SDC2026_HackstreetBoys_Stock_Manager_Pitch.pptx) |

## License

This project is licensed under [Apache License 2.0](LICENSE). Preserve applicable
third-party copyright notices and declarations in the final submission.
