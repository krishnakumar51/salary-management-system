from datetime import date
from decimal import Decimal

from app.models import Compensation, Employee, SalaryHistory


def add_employee(
    db,
    ids,
    n: int,
    *,
    first="Alex",
    last=None,
    country="IN",
    department="Engineering",
    designation="Software Engineer",
    status="active",
    employment_type="full_time",
    joining=date(2021, 3, 1),
    amount: str | None = "1000000.00",
    currency="INR",
    frequency="annual",
    email: str | None = None,
) -> Employee:
    emp = Employee(
        employee_code=f"ACME-{n:05d}",
        first_name=first,
        last_name=last or f"Tester{n}",
        email=email or f"emp{n}@acme-demo.com",
        country_id=ids["country"][country],
        department_id=ids["department"][department],
        designation=designation,
        employment_type=employment_type,
        joining_date=joining,
        status=status,
    )
    db.add(emp)
    db.flush()
    if amount is not None:
        comp = Compensation(
            employee_id=emp.id, amount=Decimal(amount), currency=currency,
            frequency=frequency, effective_date=joining,
        )
        db.add(comp)
        db.flush()
        db.add(
            SalaryHistory(
                employee_id=emp.id, compensation_id=comp.id, change_type="initial",
                new_amount=comp.amount, new_currency=currency, new_frequency=frequency,
                effective_date=joining, reason="Seeded for test",
            )
        )
    db.commit()
    return emp
