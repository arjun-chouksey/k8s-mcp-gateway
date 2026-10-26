from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from decimal import Decimal
import socket

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from pydantic import ValidationError
import pytest
import uvicorn

from analytics_mcp import (
    OrderInput,
    Settings,
    calculate_sales_trend,
    create_app,
    get_order_status_breakdown,
    get_top_products,
    summarize_sales,
)


def order(
    order_id: int, status: str, total: str, created: str, *, currency: str = "INR",
    lines: list[dict[str, object]] | None = None,
) -> OrderInput:
    return OrderInput(
        id=order_id, status=status, currency=currency, total=total, date_created=created,
        line_items=lines or [],
    )


ORDERS = [
    order(1, "processing", "100.10", "2026-10-01T10:00:00+05:30", lines=[
        {"product_id": 7, "name": "Tea", "quantity": "2", "total": "80.10"},
        {"product_id": 8, "name": "Mug", "quantity": "1", "total": "20.00"},
    ]),
    order(2, "completed", "99.90", "2026-10-02T10:00:00+05:30", lines=[
        {"product_id": 8, "name": "Mug", "quantity": "3", "total": "99.90"},
    ]),
    order(3, "cancelled", "500.00", "2026-10-08T10:00:00+05:30", lines=[
        {"product_id": 7, "name": "Tea", "quantity": "50", "total": "500.00"},
    ]),
    order(4, "refunded", "40.00", "2026-11-01T10:00:00+05:30"),
    order(5, "on-hold", "50.00", "2026-11-01T11:00:00+05:30"),
]


def test_decimal_summary_and_status_policy_include_processing_cod_value():
    result = summarize_sales(ORDERS)
    assert result["order_count"] == 5
    assert result["eligible_order_count"] == 3
    assert result["gross_order_value"] == "250.00"
    assert result["average_order_value"] == "83.33"
    assert result["currency"] == "INR"
    assert "processing" in result["status_exclusions"]
    assert "not described as settled revenue" in result["status_exclusions"]


def test_top_products_rank_by_quantity_or_revenue_and_exclude_cancelled():
    quantity = get_top_products(ORDERS, 2, "quantity")
    assert [row["product_id"] for row in quantity["products"]] == [8, 7]
    assert quantity["products"][0]["quantity_sold"] == "4"
    revenue = get_top_products(ORDERS, 2, "revenue")
    assert [row["product_id"] for row in revenue["products"]] == [8, 7]
    assert revenue["products"][0]["sales_value"] == "119.90"


def test_status_breakdown_includes_excluded_statuses_without_revenue_claim():
    result = get_order_status_breakdown(ORDERS)
    rows = {row["status"]: row for row in result["statuses"]}
    assert result["overall_order_count"] == 5
    assert rows["cancelled"] == {
        "status": "cancelled", "order_count": 1, "order_value": "500.00",
    }
    assert "not settlement" in result["value_definition"]


def test_trends_are_chronological_and_use_monday_weeks_and_months():
    daily = calculate_sales_trend(ORDERS, "day")
    assert [row["period_start"] for row in daily["buckets"]] == [
        "2026-10-01", "2026-10-02", "2026-11-01",
    ]
    weekly = calculate_sales_trend(ORDERS, "week")
    assert weekly["buckets"][0] == {
        "period_start": "2026-09-28", "order_count": 2, "order_value": "200.00",
    }
    monthly = calculate_sales_trend(ORDERS, "month")
    assert [row["order_value"] for row in monthly["buckets"]] == ["200.00", "50.00"]


def test_empty_exact_duplicate_mixed_currency_and_limits():
    assert summarize_sales([])["gross_order_value"] == "0.00"
    assert summarize_sales([ORDERS[0], ORDERS[0]])["order_count"] == 1
    with pytest.raises(ValueError, match="conflicting duplicate"):
        summarize_sales([ORDERS[0], ORDERS[0].model_copy(update={"total": Decimal("2")})])
    with pytest.raises(ValueError, match="mixed currencies"):
        summarize_sales([ORDERS[0], order(9, "completed", "1", "2026-10-01", currency="USD")])
    with pytest.raises(ValueError, match="at most 500"):
        summarize_sales([
            order(i, "completed", "1", "2026-10-01") for i in range(1, 502)
        ])
    with pytest.raises(ValueError, match="limit"):
        get_top_products([], 101, "revenue")


@pytest.mark.parametrize(
    "payload",
    [
        {"id": 1, "status": "completed", "currency": "INR", "total": "NaN", "date_created": "2026-10-01"},
        {"id": 1, "status": "completed", "currency": "INR", "total": "1", "date_created": "invalid"},
        {"id": 1, "status": "completed", "currency": "INR", "total": "1", "date_created": "2026-10-01", "email": "private@example.test"},
        {"id": 1, "status": "completed", "currency": "INR", "total": "1", "date_created": "2026-10-01", "line_items": [{"product_id": 1, "name": "X", "quantity": 0, "total": "1"}]},
    ],
)
def test_invalid_money_dates_pii_and_quantities_are_rejected(payload):
    with pytest.raises(ValidationError):
        OrderInput.model_validate(payload)


def test_woo_summary_extra_fields_are_discarded():
    order = OrderInput.model_validate({
        "id": 1, "status": "processing", "currency": "INR", "total": "499.00",
        "date_created": "2026-10-01T10:00:00Z", "payment_method": "cod",
        "line_items": [{
            "product_id": 9, "name": "Demo", "quantity": 1, "total": "499.00",
        }],
    })
    assert "payment_method" not in order.model_dump()
    assert summarize_sales([order])["gross_order_value"] == "499.00"


async def request_asgi(app, path: str, authorization: bytes | None = None) -> int:
    messages = []
    headers = [] if authorization is None else [(b"authorization", authorization)]
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    await app(
        {"type": "http", "asgi": {"version": "3.0"}, "method": "GET", "path": path,
         "raw_path": path.encode(), "query_string": b"", "headers": headers,
         "scheme": "http", "server": ("test", 80), "client": ("test", 1)},
        receive, send,
    )
    return next(message["status"] for message in messages if message["type"] == "http.response.start")


@pytest.mark.asyncio
async def test_probes_and_authentication_rejection():
    app = create_app(Settings("analytics-test-token"))
    assert await request_asgi(app, "/healthz") == 200
    assert await request_asgi(app, "/readyz") == 200
    assert await request_asgi(app, "/mcp") == 401
    assert await request_asgi(app, "/mcp", b"Bearer wrong") == 401


@asynccontextmanager
async def running_app(app):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    task = asyncio.create_task(server.serve())
    while not server.started and not task.done():
        await asyncio.sleep(0.01)
    try:
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        await task


@pytest.mark.asyncio
async def test_real_mcp_discovery_and_invocation():
    async with running_app(create_app(Settings("analytics-test-token"))) as url:
        async with httpx2.AsyncClient(
            headers={"Authorization": "Bearer analytics-test-token"}, trust_env=False,
        ) as http:
            async with Client(streamable_http_client(url, http_client=http)) as client:
                tools = await client.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    "summarize_sales", "get_top_products", "get_order_status_breakdown",
                    "calculate_sales_trend",
                }
                result = await client.call_tool(
                    "summarize_sales", {"orders": [ORDERS[0].model_dump(mode="json")]},
                )
                assert not result.is_error and "100.10" in str(result.content)
                mixed = await client.call_tool(
                    "summarize_sales", {"orders": [
                        ORDERS[0].model_dump(mode="json"),
                        order(9, "completed", "1", "2026-10-01", currency="USD").model_dump(mode="json"),
                    ]},
                )
                assert mixed.is_error
