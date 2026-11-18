"""Deterministic, database-free generation of the ACME workforce.

Same `count` + `seed` => byte-identical output on every machine. No wall-clock dependence:
all dates are relative to REFERENCE_DATE.
"""

import random
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.core.constants import ANNUALIZATION
from app.services.compensation import calculate_increment
from seed.names import DIAL_CODES, NAMES
from seed.reference import COUNTRIES, RATES

REFERENCE_DATE = date(2026, 11, 1)
DEFAULT_SEED = 20260101
EMAIL_DOMAIN = "acme-demo.com"

COUNTRY_WEIGHTS = {"IN": 34, "US": 22, "DE": 12, "GB": 12, "SG": 8, "CA": 12}
# Multiplier applied to the US-dollar salary scale (purchasing-power flavoured, fictional).
COUNTRY_PAY = {"IN": 0.28, "US": 1.0, "DE": 0.86, "GB": 0.82, "SG": 0.80, "CA": 0.85}
COUNTRY_CURRENCY = {code: cur for code, _, cur in COUNTRIES}
USD_TO = {"USD": Decimal(1), **{t: r for b, t, r, _ in RATES if b == "USD"}}

DEPT_WEIGHTS = {
    "Engineering": 30, "Sales": 14, "Product": 8, "Design": 5, "Marketing": 8,
    "Human Resources": 4, "Finance": 6, "Operations": 10, "Customer Support": 11, "Legal": 4,
}
DEPT_PAY = {
    "Engineering": 1.15, "Product": 1.10, "Legal": 1.10, "Finance": 1.0, "Design": 1.0,
    "Sales": 0.95, "Marketing": 0.90, "Human Resources": 0.85, "Operations": 0.80, "Customer Support": 0.70,
}
# Title ladders, level 1 (entry) .. 7 (executive)
LADDERS = {
    "Engineering": ["Associate Software Engineer", "Software Engineer", "Senior Software Engineer",
                    "Staff Engineer", "Engineering Manager", "Director of Engineering", "VP of Engineering"],
    "Product": ["Associate Product Manager", "Product Manager", "Senior Product Manager",
                "Group Product Manager", "Principal Product Manager", "Director of Product", "VP of Product"],
    "Design": ["Junior Designer", "Product Designer", "Senior Product Designer",
               "Lead Designer", "Design Manager", "Director of Design", "VP of Design"],
    "Sales": ["Sales Development Rep", "Account Executive", "Senior Account Executive",
              "Sales Manager", "Regional Sales Lead", "Director of Sales", "VP of Sales"],
    "Marketing": ["Marketing Associate", "Marketing Specialist", "Senior Marketing Specialist",
                  "Marketing Manager", "Head of Brand", "Director of Marketing", "VP of Marketing"],
    "Human Resources": ["HR Coordinator", "HR Generalist", "Senior HR Partner",
                        "HR Manager", "Head of Talent", "Director of People", "Chief People Officer"],
    "Finance": ["Finance Analyst", "Accountant", "Senior Accountant",
                "Finance Manager", "Financial Controller", "Director of Finance", "Chief Financial Officer"],
    "Operations": ["Operations Associate", "Operations Analyst", "Senior Operations Analyst",
                   "Operations Manager", "Head of Operations", "Director of Operations", "Chief Operating Officer"],
    "Customer Support": ["Support Associate", "Support Specialist", "Senior Support Specialist",
                         "Support Team Lead", "Support Manager", "Director of Support", "VP of Customer Success"],
    "Legal": ["Paralegal", "Legal Associate", "Senior Legal Counsel",
              "Legal Manager", "Associate General Counsel", "Deputy General Counsel", "General Counsel"],
}
LEVEL_WEIGHTS = [20, 27, 24, 13, 8, 5, 3]
LEVEL_USD = [42_000, 58_000, 80_000, 105_000, 135_000, 175_000, 240_000]
INCREMENT_PCTS = [Decimal(x) for x in ("4", "5", "6", "7.5", "8", "10", "12", "15")]
INCREMENT_REASONS = ["Annual performance review", "Promotion", "Market adjustment", "Retention adjustment"]


@dataclass
class SeedChange:
    change_type: str
    previous_amount: Decimal | None
    new_amount: Decimal
    increment_percentage: Decimal | None
    increment_amount: Decimal | None
    effective_date: date
    reason: str


@dataclass
class SeedEmployee:
    index: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: str
    country_code: str
    department: str
    designation: str
    level: int
    employment_type: str
    joining_date: date
    status: str
    currency: str
    frequency: str
    manager_index: int | None = None
    changes: list[SeedChange] = field(default_factory=list)

    @property
    def current(self) -> SeedChange:
        return self.changes[-1]


def _slug(text: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "".join(ch for ch in ascii_.lower() if ch.isalnum())


def _weighted(rng: random.Random, weights: dict[str, int]) -> str:
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def _round_to(value: Decimal, step: int) -> Decimal:
    return (value / step).quantize(Decimal(1), ROUND_HALF_UP) * step


def _phone(rng: random.Random, country: str) -> str:
    return f"{DIAL_CODES[country]} {rng.randint(200, 999)} {rng.randint(100, 999)} {rng.randint(1000, 9999)}"


def _joining_date(rng: random.Random, level: int) -> date:
    years = rng.betavariate(1.2, 2.3) * 14.5
    if level >= 5:
        years += 3
    elif level >= 4:
        years += 1.5
    years = min(years, 14.5)
    return REFERENCE_DATE - timedelta(days=int(years * 365.25) + 20)


def _current_target(rng, country: str, dept: str, level: int, currency: str, etype: str) -> Decimal:
    usd = LEVEL_USD[level - 1] * COUNTRY_PAY[country] * DEPT_PAY[dept] * rng.uniform(0.88, 1.12)
    local = Decimal(str(usd)) * USD_TO[currency]
    step = {"INR": 10_000, "EUR": 500, "USD": 1_000}[currency]
    amount = _round_to(local, step)
    if etype == "part_time":
        amount = _round_to(amount * Decimal("0.6"), step)
    elif etype == "intern":
        amount = _round_to(amount * Decimal("0.45"), step)
    return amount


def _frequency(rng: random.Random, country: str, etype: str) -> str:
    if etype == "intern":
        return "monthly"
    if etype == "contract" and rng.random() < 0.5:
        return "hourly"
    monthly_p = {"DE": 0.6, "GB": 0.6, "SG": 0.35, "IN": 0.2, "US": 0.05, "CA": 0.1}[country]
    return "monthly" if rng.random() < monthly_p else "annual"


def _to_frequency_amount(annual: Decimal, frequency: str) -> Decimal:
    value = annual / ANNUALIZATION[frequency]
    return value.quantize(Decimal("0.01"), ROUND_HALF_UP) if frequency != "annual" else annual.quantize(Decimal("0.01"))


def _build_history(rng: random.Random, e: SeedEmployee, target_annual: Decimal) -> None:
    """Walks forward from the starting salary so every history row is arithmetically exact."""
    anniversaries = [
        date(y, 4, 1)
        for y in range(e.joining_date.year, REFERENCE_DATE.year + 1)
        if e.joining_date + timedelta(days=200) <= date(y, 4, 1) <= REFERENCE_DATE
    ]
    n = min(len(anniversaries), rng.choices([0, 1, 2, 3, 4], weights=[22, 30, 25, 15, 8])[0])
    dates = anniversaries[-n:] if n else []
    steps = [(rng.choice(INCREMENT_PCTS), rng.random() < 0.15, rng.choice(INCREMENT_REASONS)) for _ in dates]

    growth = Decimal(1)
    for pct, _, _ in steps:
        growth *= 1 + pct / 100
    start = _to_frequency_amount(target_annual / growth, e.frequency)
    start = max(start, Decimal("1.00"))
    e.changes.append(SeedChange("initial", None, start, None, None, e.joining_date,
                                "Initial compensation on hire"))
    current = start
    for when, (pct, fixed, reason) in zip(dates, steps, strict=True):
        if fixed:
            inc = _round_to(current * pct / 100, 100 if e.frequency == "annual" else 10) or Decimal(10)
            new, inc_amt, inc_pct = calculate_increment(current, "fixed", Decimal(inc))
            ctype = "fixed_increment"
        else:
            new, inc_amt, inc_pct = calculate_increment(current, "percentage", pct)
            ctype = "percentage_increment"
        e.changes.append(SeedChange(ctype, current, new, inc_pct, inc_amt, when, reason))
        current = new


def generate(count: int = 10_000, seed: int = DEFAULT_SEED) -> list[SeedEmployee]:
    rng = random.Random(seed)
    used_emails: set[str] = set()
    people: list[SeedEmployee] = []
    for i in range(1, count + 1):
        country = _weighted(rng, COUNTRY_WEIGHTS)
        dept = _weighted(rng, DEPT_WEIGHTS)
        level = rng.choices(range(1, 8), weights=LEVEL_WEIGHTS)[0]
        etype = rng.choices(["full_time", "part_time", "contract", "intern"], weights=[82, 5, 9, 4])[0]
        if etype == "intern":
            level = 1
        elif etype in ("contract", "part_time"):
            level = min(level, 5)
        firsts, lasts = NAMES[country]
        first, last = rng.choice(firsts), rng.choice(lasts)
        base = f"{_slug(first)}.{_slug(last)}"
        email = f"{base}@{EMAIL_DOMAIN}"
        if email in used_emails:
            email = f"{base}{i}@{EMAIL_DOMAIN}"
        used_emails.add(email)

        joining = _joining_date(rng, level)
        status = rng.choices(["active", "on_leave", "terminated"], weights=[91, 4, 5])[0]
        if status == "terminated" and joining > REFERENCE_DATE - timedelta(days=400):
            status = "active"
        currency = COUNTRY_CURRENCY[country]
        frequency = _frequency(rng, country, etype)
        e = SeedEmployee(
            index=i, employee_code=f"ACME-{i:05d}", first_name=first, last_name=last, email=email,
            phone=_phone(rng, country), country_code=country, department=dept,
            designation=LADDERS[dept][level - 1], level=level, employment_type=etype,
            joining_date=joining, status=status, currency=currency, frequency=frequency,
        )
        annual_target = _current_target(rng, country, dept, level, currency, etype)
        if frequency == "hourly":
            annual_target = annual_target * Decimal("0.9")
        _build_history(rng, e, annual_target)
        people.append(e)

    # Reporting lines: a manager is an active, more senior colleague in the same department.
    by_dept: dict[str, list[SeedEmployee]] = {}
    for p in people:
        if p.status == "active" and p.level >= 3:
            by_dept.setdefault(p.department, []).append(p)
    for p in people:
        if p.level >= 7:
            continue
        pool = [m for m in by_dept.get(p.department, []) if m.level > p.level and m.index != p.index]
        if pool:
            p.manager_index = rng.choice(pool).index
    return people
