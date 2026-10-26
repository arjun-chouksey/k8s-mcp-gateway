from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class APIResponseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ProductFilters(StrictModel):
    search: str | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=50)


class ProductCreate(StrictModel):
    name: str = Field(min_length=1, max_length=200)
    regular_price: Decimal = Field(ge=Decimal("0"))
    description: str | None = None
    status: Literal["draft", "pending", "private", "publish"] = "publish"
    virtual: bool = True

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @field_serializer("regular_price")
    def serialize_price(self, value: Decimal) -> str:
        return format(value, "f")


class ProductSummary(APIResponseModel):
    id: int = Field(gt=0)
    name: str
    status: str
    regular_price: Decimal
    price: Decimal
    virtual: bool
    permalink: str | None = None


class OrderStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    ON_HOLD = "on-hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    FAILED = "failed"


class OrderFilters(StrictModel):
    status: OrderStatus | None = None
    after: datetime | None = None
    before: datetime | None = None
    date: Literal["today"] | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=50)

    @field_validator("after", "before")
    @classmethod
    def datetime_requires_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("datetime must include a timezone")
        return value

    def query(self, timezone: ZoneInfo, *, now: datetime | None = None) -> dict[str, str | int]:
        after = self.after
        before = self.before
        if self.date == "today":
            current = (now or datetime.now(timezone)).astimezone(timezone)
            after = datetime.combine(current.date(), time.min, timezone)
            before = datetime.combine(current.date(), time.max, timezone)
        query: dict[str, str | int] = {"page": self.page, "per_page": self.per_page}
        if self.status is not None:
            query["status"] = self.status.value
        if after is not None:
            query["after"] = after.isoformat()
        if before is not None:
            query["before"] = before.isoformat()
        return query


class LineItem(APIResponseModel):
    product_id: int
    name: str
    quantity: int
    total: Decimal


class OrderSummary(APIResponseModel):
    id: int = Field(gt=0)
    status: str
    currency: str
    total: Decimal
    date_created: datetime
    payment_method: str
    line_items: list[LineItem] = Field(default_factory=list)


class OrderDetail(OrderSummary):
    line_items: list[LineItem]
