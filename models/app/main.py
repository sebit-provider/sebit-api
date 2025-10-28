from fastapi import FastAPI

from .api.routes.asset import router as asset_router
from .api.routes.expense import router as expense_router
from .api.routes.risk import router as risk_router


def create_app() -> FastAPI:
    """Build FastAPI instance with registered routers."""
    app = FastAPI(
        title="SEBIT Engine API",
        version="0.1.0",
        description="API endpoints for SEBIT Engine financial models (asset, expense, and risk series).",
    )

    app.include_router(asset_router, prefix="/asset", tags=["Asset Models"])
    app.include_router(expense_router, prefix="/expense", tags=["Expense Models"])
    app.include_router(risk_router, prefix="/risk", tags=["Risk Models"])

    @app.get("/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        """Simple readiness check endpoint."""
        return {"status": "ok"}

    return app


app = create_app()
