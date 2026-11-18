from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, CurrentUser
from app.core.errors import conflict
from app.models import ExchangeRate
from app.schemas.common import Currency
from app.schemas.exchange_rate import ConversionOut, ExchangeRateCreate, ExchangeRateOut
from app.services import audit
from app.services import currency as fx

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


@router.get("", response_model=list[ExchangeRateOut])
def list_rates(db: DB, _: CurrentUser):
    return db.scalars(
        select(ExchangeRate).order_by(
            ExchangeRate.effective_date.desc(), ExchangeRate.base_currency, ExchangeRate.target_currency
        )
    ).all()


@router.post("", response_model=ExchangeRateOut, status_code=201)
def create_rate(body: ExchangeRateCreate, db: DB, user: CurrentUser):
    rate = ExchangeRate(**body.model_dump(), created_by=user.id)
    db.add(rate)
    try:
        db.flush()
        audit.record(
            db, user_id=user.id, action="exchange_rate.create", entity_type="exchange_rate",
            entity_id=rate.id,
            details={"pair": f"{body.base_currency}/{body.target_currency}", "rate": str(body.rate)},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise conflict(
            f"A {body.base_currency}→{body.target_currency} rate already exists for "
            f"{body.effective_date.isoformat()}."
        ) from exc
    return rate


@router.get("/convert", response_model=ConversionOut)
def convert(
    db: DB, _: CurrentUser, amount: Decimal, from_currency: Currency, to_currency: Currency,
    as_of: date | None = None,
):
    resolved = fx.require_rate(fx.load_snapshot(db, as_of), from_currency, to_currency)
    return ConversionOut(
        amount=amount, from_currency=from_currency, to_currency=to_currency,
        converted=fx.convert(amount, resolved.rate), rate=resolved.rate.quantize(Decimal("0.00000001")),
        effective_date=resolved.effective_date,
    )
