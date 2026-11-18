"""Bulk-load the deterministic ACME dataset. Run as a standalone script, never via HTTP.

    python -m seed.run                       # 10,000 employees into $DATABASE_URL
    python -m seed.run --count 500           # smaller dataset
    python -m seed.run --database-url "postgresql://...neon.tech/neondb?sslmode=require"

Safe to re-run: existing employees (matched by employee code or email) are skipped, so no
duplicates are created. Requires SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD (HR login to create).
Run `alembic upgrade head` first. Use Neon's *direct* (non-pooled) connection string for seeding.
"""

import argparse
import os
import sys
from datetime import UTC, datetime, time
from itertools import islice

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import bindparam, create_engine, insert, select, update
from sqlalchemy.orm import Session

from app.models import Compensation, Country, Department, Employee, SalaryHistory
from seed.generator import DEFAULT_SEED, SeedEmployee, generate
from seed.reference import ensure_reference_data, ensure_user

CHUNK = 1000


class SeedSettings(BaseSettings):
    """Deliberately separate from the web app's settings: seeding needs no JWT secret."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    seed_admin_email: str = Field(min_length=3)
    seed_admin_password: str = Field(min_length=8)
    seed_admin_name: str = "HR Manager"


def _normalise(url: str) -> str:
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def _chunks(items, size):
    it = iter(items)
    while batch := list(islice(it, size)):
        yield batch


def seed(db: Session, people: list[SeedEmployee], admin_id: int) -> dict[str, int]:
    countries = {c.code: c.id for c in db.scalars(select(Country))}
    departments = {d.name: d.id for d in db.scalars(select(Department))}
    existing_codes = set(db.scalars(select(Employee.employee_code)))
    existing_emails = set(db.scalars(select(Employee.email)))
    fresh = [p for p in people if p.employee_code not in existing_codes and p.email not in existing_emails]

    for batch in _chunks(fresh, CHUNK):
        db.execute(
            insert(Employee),
            [
                {
                    "employee_code": p.employee_code, "first_name": p.first_name, "last_name": p.last_name,
                    "email": p.email, "phone": p.phone, "country_id": countries[p.country_code],
                    "department_id": departments[p.department], "designation": p.designation,
                    "employment_type": p.employment_type, "joining_date": p.joining_date, "status": p.status,
                }
                for p in batch
            ],
        )
    id_by_code = {code: i for code, i in db.execute(select(Employee.employee_code, Employee.id))}
    code_of = {p.index: p.employee_code for p in people}

    for batch in _chunks(fresh, CHUNK):
        db.execute(
            insert(Compensation),
            [
                {
                    "employee_id": id_by_code[p.employee_code], "amount": p.current.new_amount,
                    "currency": p.currency, "frequency": p.frequency, "effective_date": p.current.effective_date,
                }
                for p in batch
            ],
        )
    comp_by_emp = {e: c for e, c in db.execute(select(Compensation.employee_id, Compensation.id))}

    history_rows = []
    for p in fresh:
        emp_id = id_by_code[p.employee_code]
        for c in p.changes:
            history_rows.append(
                {
                    "employee_id": emp_id, "compensation_id": comp_by_emp[emp_id],
                    "change_type": c.change_type, "previous_amount": c.previous_amount,
                    "new_amount": c.new_amount,
                    "previous_currency": None if c.previous_amount is None else p.currency,
                    "new_currency": p.currency,
                    "previous_frequency": None if c.previous_amount is None else p.frequency,
                    "new_frequency": p.frequency, "increment_percentage": c.increment_percentage,
                    "increment_amount": c.increment_amount, "effective_date": c.effective_date,
                    "reason": c.reason, "changed_by": admin_id,
                    "created_at": datetime.combine(c.effective_date, time(9, 0), tzinfo=UTC),
                }
            )
    for batch in _chunks(history_rows, CHUNK * 2):
        db.execute(insert(SalaryHistory), batch)

    managers = [
        {"b_id": id_by_code[p.employee_code], "b_mgr": id_by_code[code_of[p.manager_index]]}
        for p in fresh
        if p.manager_index is not None and code_of[p.manager_index] in id_by_code
    ]
    for batch in _chunks(managers, CHUNK):
        db.execute(
            update(Employee.__table__).where(Employee.__table__.c.id == bindparam("b_id")).values(manager_id=bindparam("b_mgr")),
            batch,
        )
    return {"inserted": len(fresh), "skipped_existing": len(people) - len(fresh), "history_rows": len(history_rows)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--count", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--database-url", help="Overrides DATABASE_URL")
    args = parser.parse_args(argv)
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    try:
        cfg = SeedSettings()  # type: ignore[call-arg]
    except Exception as exc:  # missing env => explain instead of a stack trace
        print(f"Configuration error: {exc}\nSet DATABASE_URL, SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD.", file=sys.stderr)
        return 2

    people = generate(args.count, args.seed)
    print(f"Generated {len(people)} employees (seed={args.seed}).")
    engine = create_engine(_normalise(cfg.database_url), pool_pre_ping=True)
    with Session(engine) as db, db.begin():
        ensure_reference_data(db)
        admin = ensure_user(db, cfg.seed_admin_email, cfg.seed_admin_password, cfg.seed_admin_name)
        stats = seed(db, people, admin.id)  # one transaction: all-or-nothing
    print(f"Done: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
