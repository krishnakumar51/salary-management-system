from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import Currency, ORMModel


class ExchangeRateCreate(BaseModel):
    base_currency: Currency
    target_currency: Currency
    rate: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)]
    effective_date: date
    source: str = Field(min_length=3, max_length=200)

    @model_validator(mode="after")
    def _distinct(self):
        if self.base_currency == self.target_currency:
            raise ValueError("Base and target currency must differ")
        return self


class ExchangeRateOut(ORMModel):
    id: int
    base_currency: Currency
    target_currency: Currency
    rate: Decimal
    effective_date: date
    source: str
    created_at: datetime


class ConversionOut(BaseModel):
    amount: Decimal
    from_currency: Currency
    to_currency: Currency
    converted: Decimal
    rate: Decimal
    effective_date: date | None
