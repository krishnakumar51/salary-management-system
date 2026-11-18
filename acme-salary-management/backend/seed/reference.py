"""Reference data shared by the seed script and the test-suite."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Country, Department, ExchangeRate, User
from app.core.security import hash_password

# code, name, default payroll currency.
# The platform supports INR/USD/EUR only, so UK payroll is run in EUR (assumed EU payroll entity)
# and Singapore/Canada in USD. See docs/decisions.md.
COUNTRIES = [
    ("IN", "India", "INR"),
    ("US", "United States", "USD"),
    ("DE", "Germany", "EUR"),
    ("GB", "United Kingdom", "EUR"),
    ("SG", "Singapore", "USD"),
    ("CA", "Canada", "USD"),
]

DEPARTMENTS = [
    "Engineering", "Product", "Design", "Sales", "Marketing",
    "Human Resources", "Finance", "Operations", "Customer Support", "Legal",
]

RATE_EFFECTIVE = date(2026, 1, 1)
# 1 USD = x target. INR<->EUR is derived by triangulating through USD.
RATES = [
    ("USD", "INR", Decimal("83.25000000"), "Seed data: indicative rate, update via Settings"),
    ("USD", "EUR", Decimal("0.92000000"), "Seed data: indicative rate, update via Settings"),
]


def ensure_reference_data(db: Session) -> None:
    have_c = {c.code for c in db.scalars(select(Country))}
    for code, name, cur in COUNTRIES:
        if code not in have_c:
            db.add(Country(code=code, name=name, default_currency=cur))
    have_d = {d.name for d in db.scalars(select(Department))}
    for name in DEPARTMENTS:
        if name not in have_d:
            db.add(Department(name=name))
    have_r = {(r.base_currency, r.target_currency, r.effective_date) for r in db.scalars(select(ExchangeRate))}
    for base, target, rate, source in RATES:
        if (base, target, RATE_EFFECTIVE) not in have_r:
            db.add(ExchangeRate(base_currency=base, target_currency=target, rate=rate,
                                effective_date=RATE_EFFECTIVE, source=source))
    db.flush()


def ensure_user(db: Session, email: str, password: str, full_name: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None:
        user = User(email=email.lower(), full_name=full_name, password_hash=hash_password(password))
        db.add(user)
        db.flush()
    return user


__all__ = ["COUNTRIES", "DEPARTMENTS", "RATES", "ensure_reference_data", "ensure_user"]
