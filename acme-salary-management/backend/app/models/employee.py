from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Sequence, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.compensation import Compensation
    from app.models.reference import Country, Department


# Source of auto-generated employee codes (ACME-<n>). Seeded codes use a 5-digit range below it.
employee_code_seq = Sequence("employee_code_seq", start=100001, metadata=Base.metadata)


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','on_leave','terminated')", name="status_valid"
        ),
        CheckConstraint(
            "employment_type IN ('full_time','part_time','contract','intern')",
            name="employment_type_valid",
        ),
        CheckConstraint("manager_id IS NULL OR manager_id <> id", name="no_self_manager"),
        Index("ix_employees_name", "last_name", "first_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    designation: Mapped[str] = mapped_column(String(100), index=True)
    employment_type: Mapped[str] = mapped_column(String(20), default="full_time")
    joining_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    country: Mapped["Country"] = relationship()
    department: Mapped["Department"] = relationship()
    manager: Mapped["Employee | None"] = relationship(remote_side=[id])
    compensation: Mapped["Compensation | None"] = relationship(
        back_populates="employee", uselist=False
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
