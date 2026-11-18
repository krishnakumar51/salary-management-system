from datetime import date
from decimal import Decimal
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

Currency = Literal["INR", "USD", "EUR"]
Frequency = Literal["annual", "monthly", "hourly"]
EmployeeStatus = Literal["active", "on_leave", "terminated"]
EmploymentType = Literal["full_time", "part_time", "contract", "intern"]

# Money: at most 12 integer digits + 2 decimals, never negative, never a float.
Money = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class Message(BaseModel):
    message: str


def today() -> date:
    return date.today()
