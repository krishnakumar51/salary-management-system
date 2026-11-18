from math import ceil
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import DB, CurrentUser
from app.core.errors import not_found
from app.models import Compensation, Country, Department, Employee
from app.schemas.common import Currency, Page
from app.schemas.compensation import (
    CompensationCreate,
    CompensationListItem,
    CompensationOut,
    CompensationUpdate,
    IncrementPreview,
    IncrementRequest,
)
from app.services import compensation as service

router = APIRouter(prefix="/compensation", tags=["compensation"])


@router.get("", response_model=Page[CompensationListItem])
def list_compensation(
    db: DB,
    _: CurrentUser,
    q: Annotated[str | None, Query(max_length=100)] = None,
    currency: Currency | None = None,
    department_id: int | None = None,
    employee_id: int | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    full_name = Employee.first_name + " " + Employee.last_name
    where = []
    if q and q.strip():
        pat = f"%{q.strip().replace('%', '').replace('_', '')}%"
        where.append(full_name.ilike(pat) | Employee.employee_code.ilike(pat))
    if currency:
        where.append(Compensation.currency == currency)
    if department_id:
        where.append(Employee.department_id == department_id)
    if employee_id:
        where.append(Compensation.employee_id == employee_id)

    joined = (
        select(Compensation, Employee, Department.name, Country.name)
        .join(Employee, Employee.id == Compensation.employee_id)
        .join(Department, Department.id == Employee.department_id)
        .join(Country, Country.id == Employee.country_id)
        .where(*where)
    )
    total = db.scalar(select(func.count()).select_from(joined.subquery())) or 0
    rows = db.execute(
        joined.order_by(Compensation.updated_at.desc(), Compensation.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    items = [
        CompensationListItem(
            **CompensationOut.model_validate(c).model_dump(),
            employee_code=e.employee_code,
            employee_name=e.full_name,
            department=dept,
            country=country,
            status=e.status,
        )
        for c, e, dept, country in rows
    ]
    return Page(items=items, total=total, page=page, page_size=page_size, pages=max(1, ceil(total / page_size)))


@router.post("", response_model=CompensationOut, status_code=201)
def create_compensation(body: CompensationCreate, db: DB, user: CurrentUser):
    return service.create(db, body, user)


@router.get("/{compensation_id}", response_model=CompensationOut)
def get_compensation(compensation_id: int, db: DB, _: CurrentUser):
    comp = db.get(Compensation, compensation_id)
    if comp is None:
        raise not_found("Compensation record")
    return comp


@router.patch("/{compensation_id}", response_model=CompensationOut)
def update_compensation(compensation_id: int, body: CompensationUpdate, db: DB, user: CurrentUser):
    return service.update(db, compensation_id, body, user)


@router.post("/{compensation_id}/increment/preview", response_model=IncrementPreview)
def preview_increment(compensation_id: int, body: IncrementRequest, db: DB, _: CurrentUser):
    return service.preview_increment(db, compensation_id, body)


@router.post("/{compensation_id}/increment", response_model=CompensationOut)
def apply_increment(compensation_id: int, body: IncrementRequest, db: DB, user: CurrentUser):
    return service.increment(db, compensation_id, body, user)
