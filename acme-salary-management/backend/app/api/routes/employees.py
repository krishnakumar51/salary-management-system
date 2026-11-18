from decimal import Decimal
from math import ceil
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, CurrentUser
from app.core.errors import not_found, unprocessable
from app.models import Employee, SalaryHistory, User
from app.repositories import employees as repo
from app.schemas.common import Currency, EmployeeStatus, EmploymentType, Page
from app.schemas.compensation import SalaryHistoryOut
from app.schemas.employee import EmployeeCreate, EmployeeDetail, EmployeeListItem, EmployeeUpdate
from app.services import currency as fx
from app.services import employees as service

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=Page[EmployeeListItem])
def list_employees(
    db: DB,
    _: CurrentUser,
    q: Annotated[str | None, Query(max_length=100)] = None,
    department_id: int | None = None,
    country_id: int | None = None,
    designation: str | None = None,
    status: EmployeeStatus | None = None,
    employment_type: EmploymentType | None = None,
    salary_min: Annotated[Decimal | None, Query(ge=0)] = None,
    salary_max: Annotated[Decimal | None, Query(ge=0)] = None,
    currency: Currency = "USD",
    sort: Literal["name", "joining_date", "salary", "employee_code"] = "name",
    order: Literal["asc", "desc"] = "asc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    """Salary filters/sorting compare *annual-equivalent* pay converted into `currency`."""
    filters = repo.EmployeeFilters(
        q=q, department_id=department_id, country_id=country_id, designation=designation,
        status=status, employment_type=employment_type, salary_min=salary_min, salary_max=salary_max,
    )
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        raise unprocessable(
            "Minimum salary cannot exceed maximum salary.",
            [{"field": "salary_min", "message": "Must not exceed salary_max"}],
        )
    rates = None
    if filters.uses_salary or sort == "salary":
        rates = fx.rates_to_reporting(fx.load_snapshot(db), currency)
    items, total = repo.search(
        db, filters, sort=sort, descending=order == "desc", page=page, page_size=page_size, rates=rates
    )
    return Page(
        items=items, total=total, page=page, page_size=page_size, pages=max(1, ceil(total / page_size))
    )


@router.post("", response_model=EmployeeDetail, status_code=201)
def create_employee(body: EmployeeCreate, db: DB, user: CurrentUser):
    emp = service.create(db, body, user)
    return repo.get_with_relations(db, emp.id)


@router.get("/{employee_id}", response_model=EmployeeDetail)
def get_employee(employee_id: int, db: DB, _: CurrentUser):
    emp = repo.get_with_relations(db, employee_id)
    if emp is None:
        raise not_found("Employee")
    return emp


@router.patch("/{employee_id}", response_model=EmployeeDetail)
def update_employee(employee_id: int, body: EmployeeUpdate, db: DB, user: CurrentUser):
    service.update(db, employee_id, body, user)
    return repo.get_with_relations(db, employee_id)


def _history(db: Session, employee_id: int, descending: bool) -> list[SalaryHistoryOut]:
    if db.get(Employee, employee_id) is None:
        raise not_found("Employee")
    order = (
        (SalaryHistory.effective_date.desc(), SalaryHistory.id.desc())
        if descending
        else (SalaryHistory.effective_date.asc(), SalaryHistory.id.asc())
    )
    rows = db.execute(
        select(SalaryHistory, User.full_name)
        .outerjoin(User, User.id == SalaryHistory.changed_by)
        .where(SalaryHistory.employee_id == employee_id)
        .order_by(*order)
    ).all()
    out = []
    for h, name in rows:
        item = SalaryHistoryOut.model_validate(h)
        item.changed_by_name = name
        out.append(item)
    return out


@router.get("/{employee_id}/salary-history", response_model=list[SalaryHistoryOut])
def salary_history(
    employee_id: int, db: DB, _: CurrentUser, order: Literal["asc", "desc"] = "asc"
):
    """Chronological (oldest first by default) ledger of every pay change."""
    return _history(db, employee_id, order == "desc")
