"""Reusable SQL expressions that normalise pay to an annual amount in a reporting currency."""

from sqlalchemy import ColumnElement, case

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


def reporting_expr(
    rates: dict[str, ResolvedRate],
    amount=Compensation.amount,
    frequency=Compensation.frequency,
    currency=Compensation.currency,
) -> ColumnElement:
    """Annual-equivalent amount converted to the reporting currency."""
    return case(
        *[(currency == cur, annual_expr(amount, frequency) * r.rate) for cur, r in rates.items()],
        else_=None,
    )
