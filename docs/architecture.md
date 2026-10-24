# Architecture

React interface -> FastAPI inventory and workflow APIs -> SQLAlchemy -> SQLite.

```mermaid
flowchart LR
    User[Owner or stock clerk] --> UI[React + Vite interface]
    UI -->|HTTP /api| API[FastAPI backend]
    API --> Rules[Approval rule service]
    API --> Import[CSV/XLSX import validation]
    Rules --> DB[(SQLite via SQLAlchemy)]
    Import --> DB
    API --> Payload[Simulated Orbyte JSON payload]
    Payload --> Audit[Activity log]
    Audit --> DB
```

`src/main.py` serves the built React application and API on the same port.
During development, Vite runs separately and proxies `/api` requests to FastAPI.
Orbyte integration is simulated. The application currently has no GPU workload.
