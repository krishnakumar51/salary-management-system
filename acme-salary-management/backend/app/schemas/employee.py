from datetime import date, timedelta

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import (
    Currency,
    EmployeeStatus,
    EmploymentType,
    Frequency,
    Money,
    ORMModel,
)
from app.schemas.compensation import CompensationOut

PHONE_PATTERN = r"^\+?[0-9][0-9 ()\-]{6,19}$"
CODE_PATTERN = r"^[A-Z0-9][A-Z0-9\-]{2,19}$"
Name = Field(min_length=1, max_length=80)


class CountryOut(ORMModel):
    id: int
    code: str
    name: str
    default_currency: Currency


class DepartmentOut(ORMModel):
    id: int
    name: str


class ManagerRef(ORMModel):
    id: int
    employee_code: str
    full_name: str


class InitialCompensation(BaseModel):
    amount: Money
    currency: Currency
    frequency: Frequency
    effective_date: date | None = None  # defaults to the joining date


def _check_joining(v: date) -> date:
    if v < date(1970, 1, 1):
        raise ValueError("Joining date is too far in the past")
    if v > date.today() + timedelta(days=366):
        raise ValueError("Joining date cannot be more than a year in the future")
    return v


class EmployeeCreate(BaseModel):
    employee_code: str | None = Field(default=None, pattern=CODE_PATTERN)
    first_name: str = Name
    last_name: str = Name
    email: EmailStr
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    country_id: int
    department_id: int
    designation: str = Field(min_length=2, max_length=100)
    employment_type: EmploymentType = "full_time"
    joining_date: date
    status: EmployeeStatus = "active"
    manager_id: int | None = None
    compensation: InitialCompensation | None = None

    _joining = field_validator("joining_date")(_check_joining)

    @field_validator("first_name", "last_name", "designation")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    country_id: int | None = None
    department_id: int | None = None
    designation: str | None = Field(default=None, min_length=2, max_length=100)
    employment_type: EmploymentType | None = None
    joining_date: date | None = None
    status: EmployeeStatus | None = None
    manager_id: int | None = None

    @field_validator("joining_date")
    @classmethod
    def _joining(cls, v: date | None) -> date | None:
        return _check_joining(v) if v else v

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str | None) -> str | None:
        return v.lower() if v else v


class EmployeeListItem(ORMModel):
    id: int
    employee_code: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    country: CountryOut
    department: DepartmentOut
    designation: str
    employment_type: EmploymentType
    status: EmployeeStatus
    joining_date: date
    compensation: CompensationOut | None


class EmployeeDetail(EmployeeListItem):
    phone: str | None
    manager: ManagerRef | None
