"""Shared inventory API host. Existing apps can mount the package's routers."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from backend.database import engine
from backend.schema_setup import prepare_database
from backend.routes.inventory import router as inventory_router
from backend.routes.integration import router as integration_router
from backend.routes.workflow import router as workflow_router


@asynccontextmanager
async def lifespan(app):
    prepare_database(engine)
    yield


app = FastAPI(
    title="SME Inventory API", version="1.1.0", lifespan=lifespan,
    description=(
        "Product management, stock movements, imports, transactional approvals, audit trail and simulated Orbyte sync. "
        "Currency: MYR. Minor counts auto-approve only when |delta| ≤ 2 and impact < RM50. "
        "**Hackathon demo: names are caller-supplied, not authenticated identities. "
        "Add your team's authentication and manager authorization before production use.**"
    ),
)
origins = [s.strip() for s in os.getenv("WORKFLOW_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if s.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type", "Authorization"])
app.include_router(inventory_router)
app.include_router(workflow_router)
app.include_router(integration_router)


@app.get("/", include_in_schema=False)
@app.get("/api", include_in_schema=False)
def home():
    return RedirectResponse("/docs")


@app.get("/api/healthz", tags=["Demo host"])
def health():
    return {"status": "ok", "service": "inventory-workflow"}
