from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import Currency, Frequency, Money, ORMModel, PositiveMoney

REASON = Field(min_length=3, max_length=500)


class CompensationOut(ORMModel):
    id: int
    employee_id: int
    amount: Decimal
    currency: Currency
    frequency: Frequency
    effective_date: date
    updated_at: datetime


class CompensationListItem(CompensationOut):
    employee_code: str
    employee_name: str
    department: str
    country: str
    status: str


class CompensationCreate(BaseModel):
    employee_id: int
    amount: Money
    currency: Currency
    frequency: Frequency
    effective_date: date
    reason: str = REASON


class CompensationUpdate(BaseModel):
    """Full replacement of the pay terms. Omitted currency/frequency keep their current value."""

    amount: Money
    currency: Currency | None = None
    frequency: Frequency | None = None
    effective_date: date
    reason: str = REASON


class IncrementRequest(BaseModel):
    type: Literal["percentage", "fixed"]
    value: PositiveMoney
    effective_date: date
    reason: str = REASON

    @model_validator(mode="after")
    def _percentage_bounds(self):
        if self.type == "percentage" and self.value > Decimal(1000):
            raise ValueError("Percentage increment cannot exceed 1000%")
        return self


class IncrementPreview(BaseModel):
    previous_amount: Decimal
    new_amount: Decimal
    increment_amount: Decimal
    increment_percentage: Decimal
    currency: Currency
    frequency: Frequency


class SalaryHistoryOut(ORMModel):
    id: int
    employee_id: int
    compensation_id: int
    change_type: str
    previous_amount: Decimal | None
    new_amount: Decimal
    previous_currency: str | None
    new_currency: str
    previous_frequency: str | None
    new_frequency: str
    increment_percentage: Decimal | None
    increment_amount: Decimal | None
    effective_date: date
    reason: str
    changed_by: int | None
    changed_by_name: str | None = None
    created_at: datetime
