from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import Currency


class RateUsed(BaseModel):
    from_currency: Currency
    to_currency: Currency
    rate: Decimal
    effective_date: date | None


class RateInfo(BaseModel):
    reporting_currency: Currency
    as_of: date | None  # the most recent rate date involved in the conversion
    rates: list[RateUsed]


class CountItem(BaseModel):
    id: int | None = None
    label: str
    count: int


class CurrencyTotal(BaseModel):
    currency: Currency
    employee_count: int
    total_annual: Decimal  # annual-equivalent, in the ORIGINAL currency
    total_annual_reporting: Decimal  # converted to the reporting currency


class GroupStats(BaseModel):
    id: int | None = None
    label: str
    count: int
    average: Decimal
    median: Decimal
    minimum: Decimal
    maximum: Decimal
    p25: Decimal
    p75: Decimal


class BandItem(BaseModel):
    label: str
    lower: Decimal
    upper: Decimal | None
    count: int


class RecentChange(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    change_type: str
    previous_amount: Decimal | None
    new_amount: Decimal
    previous_currency: str | None
    new_currency: str
    new_frequency: str
    increment_percentage: Decimal | None
    effective_date: date


class DashboardOut(BaseModel):
    rate_info: RateInfo
    total_employees: int
    active_employees: int
    employees_without_compensation: int
    by_country: list[CountItem]
    by_department: list[CountItem]
    by_status: list[CountItem]
    totals_by_currency: list[CurrencyTotal]
    total_compensation_reporting: Decimal
    overall: GroupStats
    department_extremes: list[GroupStats]
    salary_bands: list[BandItem]
    recent_changes: list[RecentChange]


class GroupAnalyticsOut(BaseModel):
    rate_info: RateInfo
    groups: list[GroupStats]


class DistributionOut(BaseModel):
    rate_info: RateInfo
    bands: list[BandItem]


class TrendPoint(BaseModel):
    month: str  # YYYY-MM
    changes: int
    average_increment_percentage: Decimal | None
    average_new_salary_reporting: Decimal | None


class TrendsOut(BaseModel):
    rate_info: RateInfo
    points: list[TrendPoint]


class CurrencyBreakdownOut(BaseModel):
    rate_info: RateInfo
    items: list[CurrencyTotal]

