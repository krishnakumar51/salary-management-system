from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DDL,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.employee import Employee


class Compensation(Base):
    """The *current* pay of an employee (one row per employee). History lives in salary_history."""

    __tablename__ = "compensation"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        CheckConstraint("currency IN ('INR','USD','EUR')", name="currency_valid"),
        CheckConstraint("frequency IN ('annual','monthly','hourly')", name="frequency_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), unique=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), index=True)
    frequency: Mapped[str] = mapped_column(String(10))
    effective_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee: Mapped["Employee"] = relationship(back_populates="compensation")


class SalaryHistory(Base):
    """Append-only ledger of every compensation change (enforced by a DB trigger on PostgreSQL)."""

    __tablename__ = "salary_history"
    __table_args__ = (
        CheckConstraint(
            "change_type IN ('initial','set','fixed_increment','percentage_increment')",
            name="change_type_valid",
        ),
        CheckConstraint("new_amount >= 0", name="new_amount_non_negative"),
        CheckConstraint("previous_amount IS NULL OR previous_amount >= 0", name="prev_non_negative"),
        CheckConstraint("new_currency IN ('INR','USD','EUR')", name="new_currency_valid"),
        CheckConstraint(
            "previous_currency IS NULL OR previous_currency IN ('INR','USD','EUR')",
            name="prev_currency_valid",
        ),
        Index("ix_salary_history_employee_date", "employee_id", "effective_date", "id"),
        Index("ix_salary_history_effective_date", "effective_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"))
    compensation_id: Mapped[int] = mapped_column(
        ForeignKey("compensation.id", ondelete="RESTRICT"), index=True
    )
    change_type: Mapped[str] = mapped_column(String(20))
    previous_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    new_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    previous_currency: Mapped[str | None] = mapped_column(String(3))
    new_currency: Mapped[str] = mapped_column(String(3))
    previous_frequency: Mapped[str | None] = mapped_column(String(10))
    new_frequency: Mapped[str] = mapped_column(String(10))
    increment_percentage: Mapped[Decimal | None] = mapped_column(Numeric(9, 4))
    increment_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    effective_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(String(500))
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- Immutability: reject UPDATE / DELETE on salary_history at the database level -------------
IMMUTABLE_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION salary_history_block_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'salary_history is append-only';
END;
$$ LANGUAGE plpgsql
"""
IMMUTABLE_TRIGGER_SQL = """
CREATE TRIGGER salary_history_immutable
BEFORE UPDATE OR DELETE ON salary_history
FOR EACH ROW EXECUTE FUNCTION salary_history_block_mutation()
"""

for _sql in (IMMUTABLE_FUNCTION_SQL, IMMUTABLE_TRIGGER_SQL):
    event.listen(
        SalaryHistory.__table__, "after_create", DDL(_sql).execute_if(dialect="postgresql")
    )
