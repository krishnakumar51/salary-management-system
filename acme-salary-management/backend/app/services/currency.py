"""Currency conversion on top of the exchange_rates table.

Rates are read once into a snapshot (latest rate per pair on/before `as_of`) and resolved with
pure functions, so conversion logic is easy to test and uses one query per request.

Resolution order for from -> to: identity, direct rate, inverse of the opposite pair, then
triangulation through USD (so INR <-> EUR works when only USD pairs are configured).
Original salary rows are never touched; conversion is read-time only.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import CURRENCIES, MONEY_QUANT, PIVOT_CURRENCY
from app.core.errors import unprocessable
from app.models import ExchangeRate

Snapshot = dict[tuple[str, str], tuple[Decimal, date]]


@dataclass(frozen=True)
class ResolvedRate:
    from_currency: str
    to_currency: str
    rate: Decimal
    effective_date: date | None  # None for identity; oldest involved date for derived rates


def load_snapshot(db: Session, as_of: date | None = None) -> Snapshot:
    as_of = as_of or date.today()
    rows = db.scalars(
        select(ExchangeRate)
        .where(ExchangeRate.effective_date <= as_of)
        .order_by(ExchangeRate.effective_date.asc(), ExchangeRate.id.asc())
    ).all()
    snap: Snapshot = {}
    for r in rows:  # ascending, so later rows overwrite earlier ones
        snap[(r.base_currency, r.target_currency)] = (r.rate, r.effective_date)
    return snap


def _direct_or_inverse(snap: Snapshot, frm: str, to: str) -> tuple[Decimal, date] | None:
    if (frm, to) in snap:
        return snap[(frm, to)]
    if (to, frm) in snap:
        rate, eff = snap[(to, frm)]
        return Decimal(1) / rate, eff
    return None


def resolve_rate(snap: Snapshot, frm: str, to: str) -> ResolvedRate | None:
    if frm == to:
        return ResolvedRate(frm, to, Decimal(1), None)
    hit = _direct_or_inverse(snap, frm, to)
    if hit:
        return ResolvedRate(frm, to, hit[0], hit[1])
    first = _direct_or_inverse(snap, frm, PIVOT_CURRENCY)
    second = _direct_or_inverse(snap, PIVOT_CURRENCY, to)
    if first and second:
        return ResolvedRate(frm, to, first[0] * second[0], min(first[1], second[1]))
    return None


def require_rate(snap: Snapshot, frm: str, to: str) -> ResolvedRate:
    resolved = resolve_rate(snap, frm, to)
    if resolved is None:
        raise unprocessable(
            f"No exchange rate available to convert {frm} to {to}. Add one under Settings."
        )
    return resolved


def convert(amount: Decimal, rate: Decimal) -> Decimal:
    return (amount * rate).quantize(MONEY_QUANT, ROUND_HALF_UP)


def rates_to_reporting(snap: Snapshot, reporting: str) -> dict[str, ResolvedRate]:
    """Resolved rate from every supported currency into the reporting currency."""
    return {c: require_rate(snap, c, reporting) for c in CURRENCIES}
