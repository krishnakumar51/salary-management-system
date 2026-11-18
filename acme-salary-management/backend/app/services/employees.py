from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import conflict, not_found, unprocessable
from app.models import Country, Department, Employee, User
from app.models.employee import employee_code_seq
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services import audit
from app.services import compensation as compensation_service

NON_NULLABLE = {
    "first_name", "last_name", "email", "country_id", "department_id",
    "designation", "employment_type", "joining_date", "status",
}


def _validate_refs(db: Session, *, country_id=None, department_id=None) -> None:
    if country_id is not None and db.get(Country, country_id) is None:
        raise unprocessable("Country does not exist.", [{"field": "country_id", "message": "Unknown country"}])
    if department_id is not None and db.get(Department, department_id) is None:
        raise unprocessable(
            "Department does not exist.", [{"field": "department_id", "message": "Unknown department"}]
        )


def _validate_manager(db: Session, manager_id: int | None, employee_id: int | None) -> None:
    if manager_id is None:
        return
    err = lambda msg: unprocessable(msg, [{"field": "manager_id", "message": msg}])  # noqa: E731
    if employee_id is not None and manager_id == employee_id:
        raise err("An employee cannot be their own manager")
    manager = db.get(Employee, manager_id)
    if manager is None:
        raise err("Manager does not exist")
    # Walk up the chain to refuse reporting cycles.
    seen, cursor = set(), manager
    while cursor is not None and cursor.id not in seen:
        if employee_id is not None and cursor.manager_id == employee_id:
            raise err("This would create a circular reporting line")
        seen.add(cursor.id)
        cursor = db.get(Employee, cursor.manager_id) if cursor.manager_id else None


def _translate_integrity(exc: IntegrityError):
    msg = str(exc.orig).lower()
    if "email" in msg:
        return conflict("An employee with this email already exists.", [{"field": "email", "message": "Already in use"}])
    if "employee_code" in msg:
        return conflict(
            "An employee with this employee ID already exists.",
            [{"field": "employee_code", "message": "Already in use"}],
        )
    return unprocessable("The request violates a database constraint.")


def create(db: Session, data: EmployeeCreate, user: User) -> Employee:
    _validate_refs(db, country_id=data.country_id, department_id=data.department_id)
    _validate_manager(db, data.manager_id, None)
    try:
        code = data.employee_code or f"ACME-{db.scalar(employee_code_seq.next_value())}"
        emp = Employee(
            employee_code=code,
            **data.model_dump(exclude={"employee_code", "compensation"}),
        )
        db.add(emp)
        db.flush()
        if data.compensation:
            c = data.compensation
            compensation_service.add_initial(
                db,
                emp,
                amount=c.amount,
                currency=c.currency,
                frequency=c.frequency,
                effective_date=c.effective_date or data.joining_date,
                reason="Initial compensation on hire",
                user=user,
            )
        audit.record(
            db, user_id=user.id, action="employee.create", entity_type="employee",
            entity_id=emp.id, details={"employee_code": code},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _translate_integrity(exc) from exc
    except Exception:
        db.rollback()
        raise
    return emp


def update(db: Session, employee_id: int, data: EmployeeUpdate, user: User) -> Employee:
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise not_found("Employee")
    changes = data.model_dump(exclude_unset=True)
    nulls = [k for k in changes if k in NON_NULLABLE and changes[k] is None]
    if nulls:
        raise unprocessable(
            "Required fields cannot be cleared.",
            [{"field": k, "message": "This field is required"} for k in nulls],
        )
    _validate_refs(db, country_id=changes.get("country_id"), department_id=changes.get("department_id"))
    if "manager_id" in changes:
        _validate_manager(db, changes["manager_id"], emp.id)
    before = {k: str(getattr(emp, k)) for k in changes}
    try:
        for k, v in changes.items():
            setattr(emp, k, v)
        audit.record(
            db, user_id=user.id, action="employee.update", entity_type="employee", entity_id=emp.id,
            details={"changed": {k: {"from": before[k], "to": str(v)} for k, v in changes.items()}},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _translate_integrity(exc) from exc
    except Exception:
        db.rollback()
        raise
    return emp


def exists_email(db: Session, email: str) -> bool:
    return db.scalar(select(Employee.id).where(Employee.email == email.lower())) is not None
