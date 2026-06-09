from fastapi import Depends, FastAPI

from app.api.routes import (
    dashboard,
    document_imports,
    forecast,
    health,
    invoices,
    monthly_sales,
    performance,
)
from app.core.auth import require_internal_api_token
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(health.router, prefix="/api")
    app.include_router(
        invoices.router,
        prefix="/api",
        dependencies=[Depends(require_internal_api_token)],
    )
    app.include_router(
        monthly_sales.router,
        prefix="/api",
        dependencies=[Depends(require_internal_api_token)],
    )
    app.include_router(
        dashboard.router,
        prefix="/api",
        dependencies=[Depends(require_internal_api_token)],
    )
    app.include_router(
        performance.router,
        prefix="/api",
        dependencies=[Depends(require_internal_api_token)],
    )
    app.include_router(
        forecast.router,
        prefix="/api",
        dependencies=[Depends(require_internal_api_token)],
    )
    app.include_router(
        document_imports.router,
        prefix="/api",
        dependencies=[Depends(require_internal_api_token)],
    )
    return app


app = create_app()
