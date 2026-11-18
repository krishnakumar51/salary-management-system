"""Aggregate queries. All heavy lifting (counts, averages, percentiles) happens in PostgreSQL.

Compensation analytics population: employees that have a compensation record and are not
terminated. Headcount breakdowns cover every employee.
"""

from decimal import Decimal

from sqlalchemy import ColumnElement, Select, func, literal, select
from sqlalchemy.orm import Session

from app.models import Compensation, Country, Department, Employee, SalaryHistory
from app.repositories.expressions import annual_expr, reporting_expr
from app.services.currency import ResolvedRate

Rates = dict[str, ResolvedRate]
PAID = Employee.status != "terminated"


def _d(value, places: str = "0.01") -> Decimal:
    if value is None:
        return Decimal(0)
    return Decimal(str(value)).quantize(Decimal(places))


def headcount_by(db: Session, kind: str) -> list[tuple[int | None, str, int]]:
    if kind == "country":
        stmt = (
            select(Country.id, Country.name, func.count(Employee.id))
            .join(Employee, Employee.country_id == Country.id)
            .group_by(Country.id, Country.name)
        )
    elif kind == "department":
        stmt = (
            select(Department.id, Department.name, func.count(Employee.id))
            .join(Employee, Employee.department_id == Department.id)
            .group_by(Department.id, Department.name)
        )
    else:
        stmt = select(literal(None), Employee.status, func.count(Employee.id)).group_by(Employee.status)
    stmt = stmt.order_by(func.count(Employee.id).desc())
    return [(r[0], r[1], r[2]) for r in db.execute(stmt)]


def totals(db: Session) -> tuple[int, int, int]:
    total = db.scalar(select(func.count(Employee.id))) or 0
    active = db.scalar(select(func.count(Employee.id)).where(Employee.status == "active")) or 0
    without = (
        db.scalar(
            select(func.count(Employee.id))
            .outerjoin(Compensation, Compensation.employee_id == Employee.id)
            .where(Compensation.id.is_(None), PAID)
        )
        or 0
    )
    return total, active, without


def _stats_columns(rep: ColumnElement):
    return [
        func.count(),
        func.avg(rep),
        func.percentile_cont(0.5).within_group(rep),
        func.min(rep),
        func.max(rep),
        func.percentile_cont(0.25).within_group(rep),
        func.percentile_cont(0.75).within_group(rep),
    ]


def _paid_base(stmt: Select) -> Select:
    return stmt.select_from(Employee).join(Compensation, Compensation.employee_id == Employee.id).where(PAID)


def _stats_dict(row) -> dict:
    return {
        "count": row[0],
        "average": _d(row[1]),
        "median": _d(row[2]),
        "minimum": _d(row[3]),
        "maximum": _d(row[4]),
        "p25": _d(row[5]),
        "p75": _d(row[6]),
    }


def overall_stats(db: Session, rates: Rates) -> dict:
    rep = reporting_expr(rates)
    row = db.execute(_paid_base(select(*_stats_columns(rep)))).one()
    return _stats_dict(row)


def grouped_stats(db: Session, rates: Rates, kind: str) -> list[dict]:
    rep = reporting_expr(rates)
    if kind == "country":
        gid, label = Country.id, Country.name
        join = Employee.country_id == Country.id
        target = Country
    else:
        gid, label = Department.id, Department.name
        join = Employee.department_id == Department.id
        target = Department
    stmt = (
        _paid_base(select(gid, label, *_stats_columns(rep)))
        .join(target, join)
        .group_by(gid, label)
        .order_by(label)
    )
    return [
        {"id": r[0], "label": r[1], **_stats_dict(r[2:])} for r in db.execute(stmt)
    ]


def currency_totals(db: Session, rates: Rates) -> list[dict]:
    rep = reporting_expr(rates)
    stmt = _paid_base(
        select(
            Compensation.currency,
            func.count(),
            func.sum(annual_expr()),
            func.sum(rep),
        )
    ).group_by(Compensation.currency).order_by(Compensation.currency)
    return [
        {
            "currency": r[0],
            "employee_count": r[1],
            "total_annual": _d(r[2]),
            "total_annual_reporting": _d(r[3]),
        }
        for r in db.execute(stmt)
    ]


def band_counts(
    db: Session,
    rates: Rates,
    edges: list[Decimal],
    *,
    department_id: int | None = None,
    country_id: int | None = None,
) -> list[int]:
    rep = reporting_expr(rates)
    cols = []
    for i, lo in enumerate(edges):
        hi = edges[i + 1] if i + 1 < len(edges) else None
        cond = rep >= lo if hi is None else (rep >= lo) & (rep < hi)
        cols.append(func.count().filter(cond))
    stmt = _paid_base(select(*cols))
    if department_id:
        stmt = stmt.where(Employee.department_id == department_id)
    if country_id:
        stmt = stmt.where(Employee.country_id == country_id)
    return list(db.execute(stmt).one())


def recent_changes(db: Session, limit: int = 10):
    stmt = (
        select(SalaryHistory, Employee.employee_code, Employee.first_name, Employee.last_name)
        .join(Employee, Employee.id == SalaryHistory.employee_id)
        .where(SalaryHistory.change_type != "initial")
        .order_by(SalaryHistory.effective_date.desc(), SalaryHistory.id.desc())
        .limit(limit)
    )
    return db.execute(stmt).all()


def monthly_trends(db: Session, rates: Rates, months: int = 24) -> list[dict]:
    latest = db.scalar(
        select(func.max(SalaryHistory.effective_date)).where(SalaryHistory.change_type != "initial")
    )
    if latest is None:
        return []
    month = func.to_char(SalaryHistory.effective_date, "YYYY-MM")
    rep = reporting_expr(
        rates,
        SalaryHistory.new_amount,
        SalaryHistory.new_frequency,
        SalaryHistory.new_currency,
    )
    cutoff = func.date_trunc("month", latest) - func.make_interval(0, months - 1)
    stmt = (
        select(month, func.count(), func.avg(SalaryHistory.increment_percentage), func.avg(rep))
        .where(SalaryHistory.change_type != "initial", SalaryHistory.effective_date >= cutoff)
        .group_by(month)
        .order_by(month)
    )
    return [
        {
            "month": r[0],
            "changes": r[1],
            "average_increment_percentage": _d(r[2]) if r[2] is not None else None,
            "average_new_salary_reporting": _d(r[3]) if r[3] is not None else None,
        }
        for r in db.execute(stmt)
    ]
