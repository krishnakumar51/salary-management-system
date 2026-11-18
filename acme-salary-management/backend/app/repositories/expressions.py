"""Reusable SQL expressions that normalise pay to an annual amount in a reporting currency."""

from decimal import Decimal

from sqlalchemy import ColumnElement, Numeric, case, literal

from app.core.constants import ANNUALIZATION
from app.models import Compensation
from app.services.currency import ResolvedRate


def annual_expr(amount=Compensation.amount, frequency=Compensation.frequency) -> ColumnElement:
    """Annual-equivalent amount in the row's ORIGINAL currency."""
    return case(
        (frequency == "monthly", amount * ANNUALIZATION["monthly"]),
        (frequency == "hourly", amount * ANNUALIZATION["hourly"]),
        else_=amount,
    )


# Rate parts need far more precision than money (NUMERIC(14,2)). Without an explicit type,
# SQLAlchemy gives a bound value the type of the column it combines with, and drivers that render
# bind casts (pg8000) then round e.g. 0.012012... to 0.01. Give them their own wide NUMERIC type.
RATE_TYPE = Numeric(38, 20)


def _wide(value: Decimal) -> ColumnElement:
    return literal(value, type_=RATE_TYPE)


def convert_expr(amount_expr: ColumnElement, rate: ResolvedRate) -> ColumnElement:
    """amount * num / den, exact whenever the quotient is representable."""
    scaled = amount_expr * _wide(rate.num)
    return scaled if rate.den == 1 else scaled / _wide(rate.den)


def reporting_expr(
    rates: dict[str, ResolvedRate],
    amount=Compensation.amount,
    frequency=Compensation.frequency,
    currency=Compensation.currency,
) -> ColumnElement:
    """Annual-equivalent amount converted to the reporting currency."""
    return case(
        *[(currency == cur, convert_expr(annual_expr(amount, frequency), r)) for cur, r in rates.items()],
        else_=None,
    )
