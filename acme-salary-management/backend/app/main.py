from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.db.session import get_engine


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="ACME Salary Management API",
        version="1.0.0",
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,  # bearer tokens in the Authorization header, no cookies
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    register_error_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    def health(deep: bool = False):
        """Liveness by default; `?deep=true` also verifies the database connection."""
        if deep:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def root():
        return {"service": "acme-salary-management", "health": "/health"}

    return app


app = create_app()
