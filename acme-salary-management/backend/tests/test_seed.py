from decimal import Decimal

from sqlalchemy import func, select

from app.models import Compensation, Employee, SalaryHistory
from app.services.compensation import calculate_increment
from seed.generator import generate
from seed.run import seed


def test_generation_is_deterministic():
    a, b = generate(300), generate(300)
    assert [(p.employee_code, p.email, p.current.new_amount) for p in a] == [
        (p.employee_code, p.email, p.current.new_amount) for p in b
    ]
    assert generate(50, seed=1)[0].email != generate(50, seed=2)[0].email


def test_codes_and_emails_are_unique_and_valid():
    people = generate(2000)
    assert len({p.employee_code for p in people}) == 2000
    assert len({p.email for p in people}) == 2000
    assert all(p.email.isascii() and "@" in p.email for p in people)
    assert all(p.currency in ("INR", "USD", "EUR") for p in people)
    assert all(p.current.new_amount > 0 for p in people)


def test_history_is_arithmetically_consistent():
    for p in generate(500):
        assert p.changes[0].change_type == "initial" and p.changes[0].previous_amount is None
        assert p.changes[0].effective_date == p.joining_date
        for prev, cur in zip(p.changes, p.changes[1:], strict=False):
            assert cur.previous_amount == prev.new_amount
            assert cur.effective_date >= prev.effective_date
            kind = "percentage" if cur.change_type == "percentage_increment" else "fixed"
            value = cur.increment_percentage if kind == "percentage" else cur.increment_amount
            new, _, _ = calculate_increment(cur.previous_amount, kind, Decimal(value))
            assert new == cur.new_amount


def test_dataset_is_varied():
    people = generate(3000)
    assert {p.country_code for p in people} == {"IN", "US", "DE", "GB", "SG", "CA"}
    assert {p.currency for p in people} == {"INR", "USD", "EUR"}
    assert {p.frequency for p in people} == {"annual", "monthly", "hourly"}
    assert {p.status for p in people} == {"active", "on_leave", "terminated"}
    assert len({p.department for p in people}) == 10


def test_seed_inserts_once_and_is_rerunnable(db, ref, user):
    people = generate(400)
    first = seed(db, people, user.id)
    db.commit()
    assert first["inserted"] == 400
    second = seed(db, people, user.id)
    db.commit()
    assert second == {"inserted": 0, "skipped_existing": 400, "history_rows": 0}
    assert db.scalar(select(func.count(Employee.id))) == 400
    assert db.scalar(select(func.count(Compensation.id))) == 400
    assert db.scalar(select(func.count(SalaryHistory.id))) == first["history_rows"]


def test_seeded_managers_are_valid_and_in_same_department(db, ref, user):
    seed(db, generate(600), user.id)
    db.commit()
    rows = db.execute(
        select(Employee.department_id, Employee.id, Employee.manager_id).where(Employee.manager_id.is_not(None))
    ).all()
    dept_of = {i: d for d, i, _ in db.execute(select(Employee.department_id, Employee.id, Employee.manager_id))}
    assert rows and all(dept_of[m] == d for d, _, m in rows)
