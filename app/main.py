from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_tables
from app import seed
from app.errors import DomainError, domain_error_handler
from app.settings import settings
from app.routers import auth, recipes, orders, verification, sewing

app = FastAPI(title="ApparelFlow ERP")

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register custom domain error handler
app.add_exception_handler(DomainError, domain_error_handler)

# Include all API routers under the /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(recipes.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(verification.router, prefix="/api")
app.include_router(sewing.router, prefix="/api")


@app.on_event("startup")
def on_startup() -> None:
    """Initializes database tables and seeds default data on application startup."""
    create_tables()
    seed.run()


@app.get("/api/health")
def health_check() -> dict:
    """Public health check endpoint with no database dependencies."""
    return {"status": "ok"}