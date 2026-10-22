"""Standalone demo host. Existing apps can mount just the package's routers."""
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.core import Base, Product
from backend.database import engine, get_db
from backend.routes.integration import router as integration_router
from backend.routes.workflow import router as workflow_router
from backend.schemas import ProductOut
from backend.services.inventory import list_products


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="SME Inventory · Workflow API", version="1.0.0", lifespan=lifespan,
    description=(
        "Member 3: discrepancy detection, transactional approvals, audit trail and simulated Orbyte sync. "
        "Currency: MYR. Minor counts auto-approve only when |delta| ≤ 2 and impact < RM50. "
        "**Hackathon demo: names are caller-supplied, not authenticated identities. "
        "Add your team's authentication and manager authorization before production use.**"
    ),
)
origins = [s.strip() for s in os.getenv("WORKFLOW_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if s.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization"])
app.include_router(workflow_router)
app.include_router(integration_router)


@app.get("/", include_in_schema=False)
@app.get("/api", include_in_schema=False)
def home():
    return RedirectResponse("/docs")


@app.get("/api/healthz", tags=["Demo host"])
def health():
    return {"status": "ok", "service": "inventory-workflow"}


@app.get("/api/products", response_model=list[ProductOut], tags=["Demo host"])
def products(db: Session = Depends(get_db)):
    """Standalone product picker for Swagger and Member 2; core Product CRUD stays with Member 1."""
    return list_products(db)
