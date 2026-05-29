from fastapi import FastAPI

from app.api.routes import dashboard, health, invoices, monthly_sales
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(health.router, prefix="/api")
    app.include_router(invoices.router, prefix="/api")
    app.include_router(monthly_sales.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    return app


app = create_app()
