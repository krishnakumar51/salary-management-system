from fastapi import APIRouter

from app.api.routes import analytics, auth, compensation, employees, exchange_rates, lookups

api_router = APIRouter(prefix="/api/v1")
for module in (auth, employees, compensation, analytics, exchange_rates, lookups):
    api_router.include_router(module.router)
