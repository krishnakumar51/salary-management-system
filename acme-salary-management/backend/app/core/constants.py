from decimal import Decimal

CURRENCIES = ("INR", "USD", "EUR")
FREQUENCIES = ("annual", "monthly", "hourly")
EMPLOYEE_STATUSES = ("active", "on_leave", "terminated")
EMPLOYMENT_TYPES = ("full_time", "part_time", "contract", "intern")
CHANGE_TYPES = ("initial", "set", "fixed_increment", "percentage_increment")

# Multipliers used to express any pay frequency as an annual equivalent.
# hourly assumes a 2,080-hour work year (40h x 52w).
ANNUALIZATION: dict[str, Decimal] = {
    "annual": Decimal(1),
    "monthly": Decimal(12),
    "hourly": Decimal(2080),
}
PIVOT_CURRENCY = "USD"
MONEY_QUANT = Decimal("0.01")
