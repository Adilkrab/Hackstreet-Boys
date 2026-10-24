# Stock Manager

Inventory management for Malaysian micro and small businesses: connect spreadsheet
inputs with stock movements, physical counts, owner approvals and an activity trail.

> Submission preparation: fields marked **TODO** and the PDFs in `submission/`
> are placeholders. Replace them with verified team information and completed
> official forms before submitting. Replit deployment and proof of use are pending.

## Team Information

| Field | Details |
| --- | --- |
| **Team Name** | Hackstreet-Boys - **TODO: confirm exact registered spelling** |
| **Team Domain** | Domain 2 |
| **SDG Track (1-17)** | **TODO: select the team's SDG track and explain the alignment** |
| **Team Leader** | **TODO: full registered name** |
| **University** | **TODO: university name(s)** |
| **Number of Members** | 3 |

## Links

| Resource | Link / status |
| --- | --- |
| GitHub Repository | [Adilkrab/Hackstreet-Boys](https://github.com/Adilkrab/Hackstreet-Boys) |
| Replit Project | **TODO: paste the team's Replit project URL** |
| Live Demo | **TODO: paste the accessible deployed prototype URL** |
| RunPod Endpoint | **TODO: confirm not applicable (no GPU workload), or paste the actual endpoint URL** |
| Slide Deck | **TODO: paste the accessible pitch-slide link** |
| Demo Video | **TODO: paste the 5-7 minute YouTube pitch/demo link** |

## Overview

### Problem

Malaysian micro and small businesses often track stock through spreadsheets,
paper records and manual follow-up. Differences between recorded quantities and
physical counts can be missed or corrected without a clear approval trail.

**TODO: add the team's own problem evidence and SDG justification.**

### Solution

Stock Manager combines inventory records, validated spreadsheet imports and a
physical-count workflow. Small discrepancies can be corrected automatically;
larger discrepancies wait for an owner decision. Actions are recorded in an audit log.

Current automation is rule-based, not model inference. Orbyte sync is simulated
and sends no external requests. Owner/clerk switching is a demo simulation,
not authenticated access control. **TODO: confirm the final scope against the Domain 2 brief.**

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
| Hosting / Development | Replit - **TODO: add actual usage and deployment details** |
| Development assistance | Codex / ChatGPT - **TODO: list all tools and describe each member's reviewed contributions** |

## Project Structure

```text
.
├── docs/
│   ├── API.md                         # Detailed API and workflow reference
│   ├── architecture.md                # Diagram / deployment placeholder
│   └── screenshots/                   # Add genuine screenshots here
├── runpod/
│   └── README.md                      # Deployment placeholder; not integrated
├── src/
│   ├── __init__.py
│   ├── main.py                        # Combined app entry point
│   ├── utils.py                       # Shared application paths
│   ├── backend/                       # FastAPI, database, routes and services
│   ├── frontend/                      # React app and Vite configuration
│   └── sample_data/products.csv        # Synthetic demo inventory
├── submission/
│   ├── README.md                      # Form completion instructions
│   ├── SDC2026_TeamName_Preliminary.pdf
│   ├── SDC2026_TeamName_TechDeclaration.pdf
│   ├── SDC2026_TeamName_Replit_POU.pdf
│   └── SDC2026_TeamName_Runpod_POU.pdf
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
**TODO: add the final diagram and Replit deployment screenshot in `docs/`.**

## How to Run

Requirements: Python 3.11+ and Node.js 20+. Run commands from the repository root.
There are no mandatory API credentials for the current demo.

### Option 1 - Run on Replit

1. Import this repository and select the branch containing this layout
   (`submission/template-layout` until merged).
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
5. **TODO: test in the team's actual Replit workspace and replace the project/demo links above.**

SQLite is local-file storage. Choose persistent storage/hosting for a deployment
that must retain changes across restarts or republishes; do not assume an
ephemeral or multi-instance deployment will preserve this database.

### Option 2 - Run locally (combined frontend + backend)

Create and activate a virtual environment:

```sh
python -m venv .venv
```

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

**TODO: replace this section with genuine usage from the team's account.**

- Development: **TODO: describe the actual Replit work performed.**
- Hosting: **TODO: add the deployment URL and explain the run configuration.**
- Secrets: **TODO: list configuration names only, never secret values.**
- Proof of use: [submission/SDC2026_TeamName_Replit_POU.pdf](submission/SDC2026_TeamName_Replit_POU.pdf).

The proof form is currently the blank official template. Add the required evidence
from your team's own account/project before submission.

## How We Use RunPod

The current application has no model training, fine-tuning or GPU inference.
**TODO: confirm whether RunPod is applicable to the final submission.** The
participant handbook requires RunPod for GPU work; the example template labels
this section required. If no GPU is used, record that accurately and confirm the
organizers' final instructions instead of inventing an endpoint or proof.

- Workload: **TODO: actual GPU workload, or "Not used - no GPU workload".**
- Setup / endpoint: **TODO: actual deployment details, or "Not applicable".**
- Integration: **TODO: actual request flow, or "Not applicable".**
- Proof form: [submission/SDC2026_TeamName_Runpod_POU.pdf](submission/SDC2026_TeamName_Runpod_POU.pdf).

`runpod/` is a deployment-resource placeholder. Any future GPU handler source
should go under `src/`; no template echo handler is presented as a real integration.

## Challenges & Learnings

- **TODO: explain a real integration challenge and how the team resolved it.**
- **TODO: describe what the team learned about approvals, imports or deployment.**

## Future Improvements

- **TODO: add the team's prioritized next steps, distinguishing them from implemented features.**

## Team

| Name | Role | GitHub |
| --- | --- | --- |
| **TODO: Member 1 name** | Backend, database and imports | [Decartes159](https://github.com/Decartes159) |
| **TODO: Member 2 name** | Frontend and user experience | **TODO: GitHub username** |
| **TODO: Member 3 name** | Automation and approval workflow | **TODO: GitHub username** |

**TODO: identify the registered team leader and verify all contributor details.**

## Submission Checklist

- [ ] Confirm team name, domain, SDG track, leader, university and member details.
- [ ] Add working repository, Replit project, live demo, slide deck and YouTube links.
- [ ] Complete the preliminary document and technical/tools declaration.
- [ ] Declare AI assistance, third-party libraries, datasets and other resources accurately.
- [ ] Complete Replit proof of use with evidence from the team's account.
- [ ] Complete RunPod proof if applicable; confirm no-GPU handling with the organizers.
- [ ] Rename the official forms, replacing `TeamName` with the registered team name.
- [ ] Verify both the documented run steps and the actual Replit deployment.
- [ ] Include the final code in the submitted branch; make the submitted repository public.
- [ ] Add the committee's designated GitHub accounts as collaborators.
- [ ] Check that every submitted link works without your personal login.
- [ ] Confirm no API keys, passwords or real customer data are committed.
- [ ] Submit through sdchack.my before the deadline and follow the repository freeze rules.

## Submission Documents & Templates

The files in `submission/` are unfilled copies of the official forms. Complete them
using the [official resources and tutorials](https://drive.google.com/drive/folders/1xw7c2aN8N-at8hPEULzkcU76e_FFb0Ef).
The folder layout and README headings follow the
[official submission template](https://github.com/michaelzhngg/SDC_Hackathon_Submission_Template).

## License

This project is licensed under [Apache License 2.0](LICENSE). Preserve applicable
third-party copyright notices and declarations in the final submission.
