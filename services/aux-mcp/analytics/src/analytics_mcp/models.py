from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LineItemInput(StrictModel):
    product_id: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=200)
    quantity: Decimal
    total: Decimal

    @field_validator("quantity")
    @classmethod
    def valid_quantity(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value <= 0:
            raise ValueError("quantity must be a finite positive number")
        return value

    @field_validator("total")
    @classmethod
    def valid_line_total(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value < 0:
            raise ValueError("line item total must be a finite non-negative amount")
        return value


class OrderInput(StrictModel):
    id: int = Field(gt=0)
    status: str = Field(min_length=1, max_length=40)
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    total: Decimal
    date_created: datetime
    line_items: list[LineItemInput] = Field(default_factory=list, max_length=100)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("total")
    @classmethod
    def valid_total(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value < 0:
            raise ValueError("order total must be a finite non-negative amount")
        return value
