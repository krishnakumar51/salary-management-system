from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExchangeRate(Base):
    """1 unit of base_currency = `rate` units of target_currency, valid from effective_date."""

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("base_currency", "target_currency", "effective_date", name="uq_exchange_rates_pair_date"),
        CheckConstraint("rate > 0", name="rate_positive"),
        CheckConstraint("base_currency <> target_currency", name="distinct_currencies"),
        CheckConstraint("base_currency IN ('INR','USD','EUR')", name="base_valid"),
        CheckConstraint("target_currency IN ('INR','USD','EUR')", name="target_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    base_currency: Mapped[str] = mapped_column(String(3))
    target_currency: Mapped[str] = mapped_column(String(3))
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    effective_date: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(200))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
