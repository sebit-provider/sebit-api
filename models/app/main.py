from fastapi import FastAPI

from .api.routes.analysis import router as analysis_router
from .api.routes.asset import router as asset_router
from .api.routes.expense import router as expense_router
from .api.routes.probability import router as probability_router
from .api.routes.risk import router as risk_router
from .api.routes.bridge import router as bridge_router
from .api.routes.service import router as service_router


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
    app.include_router(analysis_router, prefix="/analysis", tags=["Advanced Models"])
    app.include_router(probability_router, prefix="/probability", tags=["Probability Revaluation Models"])
    app.include_router(service_router, prefix="/service", tags=["Service Revenue Models"])
    app.include_router(bridge_router)

    @app.get("/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        """Simple readiness check endpoint."""
        return {"status": "ok"}

    return app


app = create_app()
