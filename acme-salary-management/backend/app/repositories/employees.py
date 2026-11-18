from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.orm import Session, contains_eager, joinedload

from app.models import Compensation, Employee
from app.repositories.expressions import reporting_expr
from app.services.currency import ResolvedRate

SORT_FIELDS = ("name", "joining_date", "salary", "employee_code")


@dataclass
class EmployeeFilters:
    q: str | None = None
    department_id: int | None = None
    country_id: int | None = None
    designation: str | None = None
    status: str | None = None
    employment_type: str | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None

    @property
    def uses_salary(self) -> bool:
        return self.salary_min is not None or self.salary_max is not None


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _search_clause(q: str) -> ColumnElement[bool]:
    """Every whitespace-separated term must match name, employee code or email."""
    full_name = Employee.first_name + " " + Employee.last_name
    clauses = []
    for term in q.split():
        pat = f"%{_escape_like(term)}%"
        clauses.append(
            or_(
                full_name.ilike(pat, escape="\\"),
                Employee.employee_code.ilike(pat, escape="\\"),
                Employee.email.ilike(pat, escape="\\"),
            )
        )
    return and_(*clauses)


def _conditions(f: EmployeeFilters, rates: dict[str, ResolvedRate] | None) -> list[ColumnElement[bool]]:
    conds: list[ColumnElement[bool]] = []
    if f.q and f.q.strip():
        conds.append(_search_clause(f.q))
    if f.department_id:
        conds.append(Employee.department_id == f.department_id)
    if f.country_id:
        conds.append(Employee.country_id == f.country_id)
    if f.designation:
        conds.append(Employee.designation == f.designation)
    if f.status:
        conds.append(Employee.status == f.status)
    if f.employment_type:
        conds.append(Employee.employment_type == f.employment_type)
    if f.uses_salary and rates is not None:
        expr = reporting_expr(rates)
        if f.salary_min is not None:
            conds.append(expr >= f.salary_min)
        if f.salary_max is not None:
            conds.append(expr <= f.salary_max)
    return conds


def search(
    db: Session,
    filters: EmployeeFilters,
    *,
    sort: str,
    descending: bool,
    page: int,
    page_size: int,
    rates: dict[str, ResolvedRate] | None,
) -> tuple[list[Employee], int]:
    conds = _conditions(filters, rates)

    base = select(Employee).outerjoin(Compensation, Compensation.employee_id == Employee.id)
    count_q = select(func.count(Employee.id)).select_from(Employee).outerjoin(
        Compensation, Compensation.employee_id == Employee.id
    )
    for c in conds:
        base = base.where(c)
        count_q = count_q.where(c)
    total = db.scalar(count_q) or 0

    if sort == "salary" and rates is not None:
        key = reporting_expr(rates)
        order = [key.desc().nulls_last() if descending else key.asc().nulls_last()]
    elif sort == "joining_date":
        order = [Employee.joining_date.desc() if descending else Employee.joining_date.asc()]
    elif sort == "employee_code":
        order = [Employee.employee_code.desc() if descending else Employee.employee_code.asc()]
    else:
        order = (
            [Employee.last_name.desc(), Employee.first_name.desc()]
            if descending
            else [Employee.last_name.asc(), Employee.first_name.asc()]
        )
    order.append(Employee.id.asc())  # deterministic pagination

    stmt = (
        base.options(
            contains_eager(Employee.compensation),
            joinedload(Employee.country),
            joinedload(Employee.department),
        )
        .order_by(*order)
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return list(db.scalars(stmt).unique().all()), total


def get_with_relations(db: Session, employee_id: int) -> Employee | None:
    return db.scalar(
        select(Employee)
        .where(Employee.id == employee_id)
        .options(
            joinedload(Employee.country),
            joinedload(Employee.department),
            joinedload(Employee.compensation),
            joinedload(Employee.manager),
        )
    )


def distinct_designations(db: Session) -> list[str]:
    return list(db.scalars(select(Employee.designation).distinct().order_by(Employee.designation)))

