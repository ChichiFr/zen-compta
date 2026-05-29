from fastapi import FastAPI

from app.api.routes import health, invoices
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(health.router, prefix="/api")
    app.include_router(invoices.router, prefix="/api")
    return app


app = create_app()
