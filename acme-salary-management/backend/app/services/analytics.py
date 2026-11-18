from datetime import date
from decimal import Decimal
from math import floor, log10

from sqlalchemy.orm import Session

from app.repositories import analytics as repo
from app.schemas.analytics import (
    BandItem,
    CountItem,
    CurrencyBreakdownOut,
    CurrencyTotal,
    DashboardOut,
    DistributionOut,
    GroupAnalyticsOut,
    GroupStats,
    RateInfo,
    RateUsed,
    RecentChange,
    TrendPoint,
    TrendsOut,
)
from app.services import currency as fx

# Salary band edges expressed in USD (annual); converted to the reporting currency and
# rounded to 2 significant figures so labels stay readable (e.g. INR 2.5M, not 2,497,500).
BAND_EDGES_USD = [Decimal(x) for x in (0, 30_000, 60_000, 90_000, 120_000, 160_000, 220_000)]


def _round_sig(value: Decimal, figures: int = 2) -> Decimal:
    if value == 0:
        return Decimal(0)
    exp = floor(log10(abs(float(value)))) - figures + 1
    q = Decimal(10) ** exp
    return (value / q).quantize(Decimal(1)) * q


def _compact(n: Decimal) -> str:
    n = Decimal(n)
    for limit, suffix in ((Decimal(10**9), "B"), (Decimal(10**6), "M"), (Decimal(10**3), "K")):
        if n >= limit:
            text = f"{(n / limit).normalize():f}"
            return f"{text}{suffix}"
    return f"{n.normalize():f}"


class Context:
    """Rates snapshot + reporting currency for one analytics request."""

    def __init__(self, db: Session, reporting: str, as_of: date | None = None):
        self.reporting = reporting
        self.snapshot = fx.load_snapshot(db, as_of)
        self.rates = fx.rates_to_reporting(self.snapshot, reporting)

    @property
    def info(self) -> RateInfo:
        dates = [r.effective_date for r in self.rates.values() if r.effective_date]
        return RateInfo(
            reporting_currency=self.reporting,  # type: ignore[arg-type]
            as_of=max(dates) if dates else None,
            rates=[
                RateUsed(
                    from_currency=r.from_currency,  # type: ignore[arg-type]
                    to_currency=r.to_currency,  # type: ignore[arg-type]
                    rate=r.rate.quantize(Decimal("0.00000001")),
                    effective_date=r.effective_date,
                )
                for r in self.rates.values()
                if r.from_currency != r.to_currency
            ],
        )


def _bands(ctx: Context, counts_edges: list[Decimal]) -> list[Decimal]:
    factor = fx.require_rate(ctx.snapshot, "USD", ctx.reporting).rate
    return [_round_sig(e * factor) if e else Decimal(0) for e in counts_edges]


def _band_items(edges: list[Decimal], counts: list[int]) -> list[BandItem]:
    items = []
    for i, lo in enumerate(edges):
        hi = edges[i + 1] if i + 1 < len(edges) else None
        label = f"{_compact(lo)}+" if hi is None else f"{_compact(lo)}–{_compact(hi)}"
        items.append(BandItem(label=label, lower=lo, upper=hi, count=counts[i]))
    return items


def _group(rows: list[dict]) -> list[GroupStats]:
    return [GroupStats(**r) for r in rows]


def dashboard(db: Session, reporting: str) -> DashboardOut:
    ctx = Context(db, reporting)
    total, active, without = repo.totals(db)
    currency_rows = repo.currency_totals(db, ctx.rates)
    edges = _bands(ctx, BAND_EDGES_USD)
    band_counts = repo.band_counts(db, ctx.rates, edges)
    overall = repo.overall_stats(db, ctx.rates)
    recent = [
        RecentChange(
            id=h.id,
            employee_id=h.employee_id,
            employee_code=code,
            employee_name=f"{first} {last}",
            change_type=h.change_type,
            previous_amount=h.previous_amount,
            new_amount=h.new_amount,
            previous_currency=h.previous_currency,
            new_currency=h.new_currency,
            new_frequency=h.new_frequency,
            increment_percentage=h.increment_percentage,
            effective_date=h.effective_date,
        )
        for h, code, first, last in repo.recent_changes(db)
    ]
    return DashboardOut(
        rate_info=ctx.info,
        total_employees=total,
        active_employees=active,
        employees_without_compensation=without,
        by_country=[CountItem(id=i, label=l, count=c) for i, l, c in repo.headcount_by(db, "country")],
        by_department=[CountItem(id=i, label=l, count=c) for i, l, c in repo.headcount_by(db, "department")],
        by_status=[CountItem(id=None, label=l, count=c) for _, l, c in repo.headcount_by(db, "status")],
        totals_by_currency=[CurrencyTotal(**r) for r in currency_rows],
        total_compensation_reporting=sum((r["total_annual_reporting"] for r in currency_rows), Decimal(0)),
        overall=GroupStats(label="All employees", **overall),
        department_extremes=_group(repo.grouped_stats(db, ctx.rates, "department")),
        salary_bands=_band_items(edges, band_counts),
        recent_changes=recent,
    )


def by_group(db: Session, reporting: str, kind: str) -> GroupAnalyticsOut:
    ctx = Context(db, reporting)
    return GroupAnalyticsOut(rate_info=ctx.info, groups=_group(repo.grouped_stats(db, ctx.rates, kind)))


def distribution(
    db: Session, reporting: str, department_id: int | None, country_id: int | None
) -> DistributionOut:
    ctx = Context(db, reporting)
    edges = _bands(ctx, BAND_EDGES_USD)
    counts = repo.band_counts(db, ctx.rates, edges, department_id=department_id, country_id=country_id)
    return DistributionOut(rate_info=ctx.info, bands=_band_items(edges, counts))


def trends(db: Session, reporting: str) -> TrendsOut:
    ctx = Context(db, reporting)
    return TrendsOut(
        rate_info=ctx.info, points=[TrendPoint(**p) for p in repo.monthly_trends(db, ctx.rates)]
    )


def currencies(db: Session, reporting: str) -> CurrencyBreakdownOut:
    ctx = Context(db, reporting)
    return CurrencyBreakdownOut(
        rate_info=ctx.info, items=[CurrencyTotal(**r) for r in repo.currency_totals(db, ctx.rates)]
    )
