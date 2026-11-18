from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DB, CurrentUser
from app.schemas.analytics import (
    CurrencyBreakdownOut,
    DashboardOut,
    DistributionOut,
    GroupAnalyticsOut,
    TrendsOut,
)
from app.schemas.common import Currency
from app.services import analytics as service

router = APIRouter(prefix="/analytics", tags=["analytics"])
Reporting = Annotated[Currency, Query(description="Reporting currency for converted values")]


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: DB, _: CurrentUser, currency: Reporting = "USD"):
    return service.dashboard(db, currency)


@router.get("/departments", response_model=GroupAnalyticsOut)
def departments(db: DB, _: CurrentUser, currency: Reporting = "USD"):
    return service.by_group(db, currency, "department")


@router.get("/countries", response_model=GroupAnalyticsOut)
def countries(db: DB, _: CurrentUser, currency: Reporting = "USD"):
    return service.by_group(db, currency, "country")


@router.get("/distribution", response_model=DistributionOut)
def distribution(
    db: DB,
    _: CurrentUser,
    currency: Reporting = "USD",
    department_id: int | None = None,
    country_id: int | None = None,
):
    return service.distribution(db, currency, department_id, country_id)


@router.get("/trends", response_model=TrendsOut)
def trends(db: DB, _: CurrentUser, currency: Reporting = "USD"):
    return service.trends(db, currency)


@router.get("/currencies", response_model=CurrencyBreakdownOut)
def currencies(db: DB, _: CurrentUser, currency: Reporting = "USD"):
    return service.currencies(db, currency)
