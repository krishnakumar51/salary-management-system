from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.core.constants import CURRENCIES, EMPLOYEE_STATUSES, EMPLOYMENT_TYPES, FREQUENCIES
from app.models import Country, Department
from app.repositories.employees import distinct_designations
from app.schemas.employee import CountryOut, DepartmentOut

router = APIRouter(prefix="/lookups", tags=["lookups"])


class LookupsOut(BaseModel):
    countries: list[CountryOut]
    departments: list[DepartmentOut]
    designations: list[str]
    currencies: list[str]
    frequencies: list[str]
    statuses: list[str]
    employment_types: list[str]


@router.get("", response_model=LookupsOut)
def lookups(db: DB, _: CurrentUser):
    return LookupsOut(
        countries=db.scalars(select(Country).order_by(Country.name)).all(),
        departments=db.scalars(select(Department).order_by(Department.name)).all(),
        designations=distinct_designations(db),
        currencies=list(CURRENCIES),
        frequencies=list(FREQUENCIES),
        statuses=list(EMPLOYEE_STATUSES),
        employment_types=list(EMPLOYMENT_TYPES),
    )
