"""Compensation changes. Every public function is one atomic unit of work:
the compensation row, the salary_history row and the audit log are committed together
or not at all.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.constants import MONEY_QUANT
from app.core.errors import conflict, not_found, unprocessable
from app.models import Compensation, Employee, SalaryHistory, User
from app.schemas.compensation import (
    CompensationCreate,
    CompensationUpdate,
    IncrementPreview,
    IncrementRequest,
)
from app.services import audit

HUNDRED = Decimal(100)


def calculate_increment(
    current: Decimal, kind: str, value: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    """Returns (new_amount, increment_amount, increment_percentage). Pure Decimal maths."""
    if kind == "percentage":
        increment = (current * value / HUNDRED).quantize(MONEY_QUANT, ROUND_HALF_UP)
        pct = value
    else:
        increment = value.quantize(MONEY_QUANT, ROUND_HALF_UP)
        pct = (
            (increment / current * HUNDRED).quantize(Decimal("0.0001"), ROUND_HALF_UP)
            if current > 0
            else Decimal(0)
        )
    return current + increment, increment, pct


def _lock_compensation(db: Session, compensation_id: int) -> Compensation:
    comp = db.scalar(
        select(Compensation).where(Compensation.id == compensation_id).with_for_update()
    )
    if comp is None:
        raise not_found("Compensation record")
    return comp


def _ensure_payable(employee: Employee) -> None:
    if employee.status == "terminated":
        raise conflict("Compensation cannot be changed for a terminated employee.")


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise unprocessable("Compensation violates a database constraint.") from exc
    except Exception:
        db.rollback()
        raise


def _commit_and_refresh(db: Session, comp: Compensation) -> None:
    _commit(db)
    db.refresh(comp)  # return what the database stored (NUMERIC scale, server timestamps)


def add_initial(
    db: Session,
    employee: Employee,
    *,
    amount: Decimal,
    currency: str,
    frequency: str,
    effective_date: date,
    reason: str,
    user: User | None,
) -> Compensation:
    """Creates the compensation + 'initial' history row in the caller's transaction (no commit)."""
    comp = Compensation(
        employee_id=employee.id,
        amount=amount,
        currency=currency,
        frequency=frequency,
        effective_date=effective_date,
    )
    db.add(comp)
    db.flush()
    db.add(
        SalaryHistory(
            employee_id=employee.id,
            compensation_id=comp.id,
            change_type="initial",
            previous_amount=None,
            new_amount=amount,
            previous_currency=None,
            new_currency=currency,
            previous_frequency=None,
            new_frequency=frequency,
            effective_date=effective_date,
            reason=reason,
            changed_by=user.id if user else None,
        )
    )
    audit.record(
        db,
        user_id=user.id if user else None,
        action="compensation.create",
        entity_type="compensation",
        entity_id=comp.id,
        details={"employee_id": employee.id, "amount": str(amount), "currency": currency},
    )
    return comp


def create(db: Session, data: CompensationCreate, user: User) -> Compensation:
    employee = db.get(Employee, data.employee_id)
    if employee is None:
        raise not_found("Employee")
    _ensure_payable(employee)
    exists = db.scalar(select(Compensation.id).where(Compensation.employee_id == employee.id))
    if exists:
        raise conflict("This employee already has a compensation record; update it instead.")
    comp = add_initial(
        db,
        employee,
        amount=data.amount,
        currency=data.currency,
        frequency=data.frequency,
        effective_date=data.effective_date,
        reason=data.reason,
        user=user,
    )
    _commit_and_refresh(db, comp)
    return comp


def _apply_change(
    db: Session,
    comp: Compensation,
    *,
    change_type: str,
    new_amount: Decimal,
    new_currency: str,
    new_frequency: str,
    effective_date: date,
    reason: str,
    user: User,
    increment_percentage: Decimal | None = None,
    increment_amount: Decimal | None = None,
) -> None:
    employee = db.get(Employee, comp.employee_id)
    assert employee is not None
    _ensure_payable(employee)
    if effective_date < comp.effective_date:
        raise unprocessable(
            f"Effective date cannot be earlier than the current compensation's effective date "
            f"({comp.effective_date.isoformat()})."
        )
    if new_amount < 0:
        raise unprocessable("Resulting salary cannot be negative.")

    history = SalaryHistory(
        employee_id=comp.employee_id,
        compensation_id=comp.id,
        change_type=change_type,
        previous_amount=comp.amount,
        new_amount=new_amount,
        previous_currency=comp.currency,
        new_currency=new_currency,
        previous_frequency=comp.frequency,
        new_frequency=new_frequency,
        increment_percentage=increment_percentage,
        increment_amount=increment_amount,
        effective_date=effective_date,
        reason=reason,
        changed_by=user.id,
    )
    comp.amount = new_amount
    comp.currency = new_currency
    comp.frequency = new_frequency
    comp.effective_date = effective_date
    db.add(history)
    audit.record(
        db,
        user_id=user.id,
        action=f"compensation.{change_type}",
        entity_type="compensation",
        entity_id=comp.id,
        details={
            "employee_id": comp.employee_id,
            "from": str(history.previous_amount),
            "to": str(new_amount),
            "currency": new_currency,
        },
    )


def update(db: Session, compensation_id: int, data: CompensationUpdate, user: User) -> Compensation:
    try:
        comp = _lock_compensation(db, compensation_id)
        _apply_change(
            db,
            comp,
            change_type="set",
            new_amount=data.amount,
            new_currency=data.currency or comp.currency,
            new_frequency=data.frequency or comp.frequency,
            effective_date=data.effective_date,
            reason=data.reason,
            user=user,
        )
        _commit_and_refresh(db, comp)
    except Exception:
        db.rollback()
        raise
    return comp


def preview_increment(db: Session, compensation_id: int, data: IncrementRequest) -> IncrementPreview:
    comp = db.get(Compensation, compensation_id)
    if comp is None:
        raise not_found("Compensation record")
    new_amount, inc, pct = calculate_increment(comp.amount, data.type, data.value)
    return IncrementPreview(
        previous_amount=comp.amount,
        new_amount=new_amount,
        increment_amount=inc,
        increment_percentage=pct,
        currency=comp.currency,  # type: ignore[arg-type]
        frequency=comp.frequency,  # type: ignore[arg-type]
    )


def increment(db: Session, compensation_id: int, data: IncrementRequest, user: User) -> Compensation:
    try:
        comp = _lock_compensation(db, compensation_id)
        new_amount, inc, pct = calculate_increment(comp.amount, data.type, data.value)
        _apply_change(
            db,
            comp,
            change_type="percentage_increment" if data.type == "percentage" else "fixed_increment",
            new_amount=new_amount,
            new_currency=comp.currency,
            new_frequency=comp.frequency,
            effective_date=data.effective_date,
            reason=data.reason,
            user=user,
            increment_percentage=pct,
            increment_amount=inc,
        )
        _commit_and_refresh(db, comp)
    except Exception:
        db.rollback()
        raise
    return comp
