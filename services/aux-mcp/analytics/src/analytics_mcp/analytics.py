from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from .models import OrderInput


MAX_ORDERS = 500
MAX_TOP_PRODUCTS = 100
ELIGIBLE_STATUSES = frozenset({"processing", "completed", "on-hold"})
STATUS_POLICY = (
    "Bookable order value includes processing, completed, and on-hold orders. "
    "Pending, cancelled, refunded, failed, checkout-draft, and unknown statuses are excluded. "
    "Processing COD orders are included as booked order value, not described as settled revenue. "
    "Partial refund amounts are unavailable in this input contract and therefore are not netted."
)
COVERAGE_NOTE = (
    "Computed only from the supplied order page(s); fetch and pass every page before treating "
    "the result as a complete store total."
)


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")


def _quantity(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _orders(orders: list[OrderInput]) -> list[OrderInput]:
    if len(orders) > MAX_ORDERS:
        raise ValueError(f"at most {MAX_ORDERS} orders may be processed per call")
    unique: dict[int, OrderInput] = {}
    for order in orders:
        existing = unique.get(order.id)
        if existing is None:
            unique[order.id] = order
        elif existing != order:
            raise ValueError(f"conflicting duplicate order id: {order.id}")
    currencies = {order.currency for order in unique.values()}
    if len(currencies) > 1:
        raise ValueError("mixed currencies are not supported; analyze each currency separately")
    return list(unique.values())


def summarize_sales(orders: list[OrderInput]) -> dict[str, object]:
    normalized = _orders(orders)
    eligible = [order for order in normalized if order.status in ELIGIBLE_STATUSES]
    gross = sum((order.total for order in eligible), Decimal("0"))
    average = gross / len(eligible) if eligible else Decimal("0")
    return {
        "order_count": len(normalized),
        "eligible_order_count": len(eligible),
        "gross_order_value": _money(gross),
        "average_order_value": _money(average),
        "currency": normalized[0].currency if normalized else None,
        "status_exclusions": STATUS_POLICY,
        "coverage_note": COVERAGE_NOTE,
    }


def get_top_products(
    orders: list[OrderInput], limit: int = 10, rank_by: Literal["quantity", "revenue"] = "revenue"
) -> dict[str, object]:
    if not 1 <= limit <= MAX_TOP_PRODUCTS:
        raise ValueError(f"limit must be between 1 and {MAX_TOP_PRODUCTS}")
    normalized = _orders(orders)
    totals: dict[tuple[int, str], dict[str, Decimal]] = defaultdict(
        lambda: {"quantity": Decimal("0"), "revenue": Decimal("0")}
    )
    for order in normalized:
        if order.status not in ELIGIBLE_STATUSES:
            continue
        for item in order.line_items:
            totals[(item.product_id, item.name)]["quantity"] += item.quantity
            totals[(item.product_id, item.name)]["revenue"] += item.total
    ranked = sorted(
        totals.items(),
        key=lambda item: (-item[1][rank_by], item[0][0], item[0][1].casefold()),
    )[:limit]
    return {
        "rank_by": rank_by,
        "currency": normalized[0].currency if normalized else None,
        "products": [
            {
                "rank": rank,
                "product_id": product[0],
                "name": product[1],
                "quantity_sold": _quantity(values["quantity"]),
                "sales_value": _money(values["revenue"]),
            }
            for rank, (product, values) in enumerate(ranked, start=1)
        ],
        "status_exclusions": STATUS_POLICY,
        "coverage_note": COVERAGE_NOTE,
    }


def get_order_status_breakdown(orders: list[OrderInput]) -> dict[str, object]:
    normalized = _orders(orders)
    breakdown: dict[str, dict[str, object]] = {}
    for order in normalized:
        row = breakdown.setdefault(order.status, {"order_count": 0, "order_value": Decimal("0")})
        row["order_count"] = int(row["order_count"]) + 1
        row["order_value"] = Decimal(row["order_value"]) + order.total
    return {
        "overall_order_count": len(normalized),
        "currency": normalized[0].currency if normalized else None,
        "statuses": [
            {
                "status": status,
                "order_count": values["order_count"],
                "order_value": _money(Decimal(values["order_value"])),
            }
            for status, values in sorted(breakdown.items())
        ],
        "value_definition": "Order total by status; values are not settlement or net-revenue claims.",
        "coverage_note": COVERAGE_NOTE,
    }


def _bucket_start(value: date, interval: str) -> date:
    if interval == "day":
        return value
    if interval == "week":
        return value - timedelta(days=value.weekday())
    return value.replace(day=1)


def calculate_sales_trend(
    orders: list[OrderInput], interval: Literal["day", "week", "month"]
) -> dict[str, object]:
    normalized = _orders(orders)
    buckets: dict[date, dict[str, object]] = {}
    for order in normalized:
        if order.status not in ELIGIBLE_STATUSES:
            continue
        key = _bucket_start(order.date_created.date(), interval)
        row = buckets.setdefault(key, {"order_count": 0, "order_value": Decimal("0")})
        row["order_count"] = int(row["order_count"]) + 1
        row["order_value"] = Decimal(row["order_value"]) + order.total
    return {
        "interval": interval,
        "currency": normalized[0].currency if normalized else None,
        "buckets": [
            {
                "period_start": key.isoformat(),
                "order_count": values["order_count"],
                "order_value": _money(Decimal(values["order_value"])),
            }
            for key, values in sorted(buckets.items())
        ],
        "status_exclusions": STATUS_POLICY,
        "coverage_note": COVERAGE_NOTE,
    }
