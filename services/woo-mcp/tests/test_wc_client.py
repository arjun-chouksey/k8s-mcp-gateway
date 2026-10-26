import asyncio
from datetime import datetime
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import httpx
import pytest
from pydantic import ValidationError

from woo_mcp import (
    OrderFilters,
    OrderStatus,
    ProductCreate,
    ProductFilters,
    WCAuthenticationError,
    WCClient,
    WCNotFoundError,
    WCUncertainWriteError,
    WCUpstreamError,
    WCValidationError,
)


PRODUCT = {
    "id": 7,
    "name": "Demo",
    "status": "publish",
    "regular_price": "19.90",
    "price": "19.90",
    "virtual": True,
    "permalink": "http://shop.example/products/demo",
    "meta_data": [{"key": "private", "value": "not projected"}],
}

ORDER = {
    "id": 12,
    "status": "processing",
    "currency": "INR",
    "total": "998.00",
    "date_created": "2026-10-15T20:00:00+05:30",
    "payment_method": "cod",
    "line_items": [{"product_id": 10, "name": "Demo", "quantity": 2, "total": "998.00"}],
    "billing": {"email": "customer@example.com", "phone": "+91-secret"},
    "shipping": {"address_1": "private address"},
}


def run(coro):
    return asyncio.run(coro)


def make_client(handler):
    return WCClient(
        base_url="http://wordpress.store.svc.cluster.local",
        oauth_base_url="http://shop.127.0.0.1.nip.io:8080",
        consumer_key="ck_test_key",
        consumer_secret="cs_test_secret",
        transport=httpx.MockTransport(handler),
    )


def test_list_products_signs_canonical_url_without_leaking_secret():
    async def scenario():
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.host == "wordpress.store.svc.cluster.local"
            params = parse_qs(urlsplit(str(request.url)).query)
            assert params["oauth_consumer_key"] == ["ck_test_key"]
            assert params["oauth_signature_method"] == ["HMAC-SHA256"]
            assert "cs_test_secret" not in str(request.url)
            return httpx.Response(200, json=[PRODUCT])

        async with make_client(handler) as client:
            products = await client.list_products(ProductFilters(search="Demo"))
            assert products[0].regular_price == Decimal("19.90")
            assert "meta_data" not in products[0].model_dump()

    run(scenario())


def test_create_product_serializes_decimal_and_makes_one_attempt():
    async def scenario():
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            assert request.method == "POST"
            assert request.read().decode().find('"regular_price":"10.50"') >= 0
            return httpx.Response(201, json={**PRODUCT, "regular_price": "10.50", "price": "10.50"})

        async with make_client(handler) as client:
            product = await client.create_product(ProductCreate(name=" New product ", regular_price=Decimal("10.50")))
            assert product.name == "Demo"
            assert calls == 1

    run(scenario())


def test_write_timeout_is_uncertain_and_never_retried():
    async def scenario():
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            raise httpx.ReadTimeout("secret and customer@example.com", request=request)

        async with make_client(handler) as client:
            with pytest.raises(WCUncertainWriteError, match="outcome is unknown") as captured:
                await client.create_product(ProductCreate(name="Probe", regular_price=Decimal("1.00")))
            assert calls == 1
            assert "secret" not in str(captured.value)
            assert "customer@example.com" not in str(captured.value)

    run(scenario())


@pytest.mark.parametrize(
    ("status", "exception"),
    [
        (400, WCValidationError),
        (401, WCAuthenticationError),
        (403, WCAuthenticationError),
        (404, WCNotFoundError),
        (500, WCUpstreamError),
    ],
)
def test_http_errors_are_mapped_without_response_details(status, exception):
    async def scenario():
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status,
                json={"code": "woocommerce_rest_error", "message": "ck_secret customer@example.com"},
            )

        async with make_client(handler) as client:
            with pytest.raises(exception) as captured:
                await client.list_products(ProductFilters())
            assert "ck_secret" not in str(captured.value)
            assert "customer@example.com" not in str(captured.value)

    run(scenario())


def test_order_methods_project_pii_and_update_status_once():
    async def scenario():
        methods = []

        def handler(request: httpx.Request) -> httpx.Response:
            methods.append(request.method)
            if request.method == "GET" and request.url.path.endswith("/orders"):
                return httpx.Response(200, json=[ORDER])
            if request.method == "PUT":
                assert request.read() == b'{"status":"completed"}'
                return httpx.Response(200, json={**ORDER, "status": "completed"})
            return httpx.Response(200, json=ORDER)

        async with make_client(handler) as client:
            orders = await client.list_orders(OrderFilters(status=OrderStatus.PROCESSING))
            assert orders[0].line_items[0].product_id == ORDER["line_items"][0]["product_id"]
            order = await client.get_order(orders[0].id)
            updated = await client.update_order_status(order.id, OrderStatus.COMPLETED)
            assert updated.status == "completed"
            assert "billing" not in order.model_dump()
            assert "shipping" not in order.model_dump()
            assert methods == ["GET", "GET", "PUT"]

    run(scenario())


def test_today_filter_uses_store_timezone_boundaries():
    filters = OrderFilters(date="today")
    now = datetime(2026, 10, 16, 23, 45, tzinfo=ZoneInfo("Asia/Kolkata"))
    query = filters.query(ZoneInfo("Asia/Kolkata"), now=now)
    assert query["after"] == "2026-10-16T00:00:00+05:30"
    assert query["before"] == "2026-10-16T23:59:59.999999+05:30"


def test_models_reject_blank_names_naive_dates_and_invalid_statuses():
    with pytest.raises(ValidationError):
        ProductCreate(name="  ", regular_price=Decimal("1"))
    with pytest.raises(ValidationError):
        OrderFilters(after=datetime(2026, 10, 16))
    with pytest.raises(ValueError):
        OrderStatus("not-a-status")


def test_invalid_response_does_not_leak_customer_data():
    async def scenario():
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[{"billing": {"email": "customer@example.com"}}])

        async with make_client(handler) as client:
            with pytest.raises(WCUpstreamError) as captured:
                await client.list_products(ProductFilters())
            assert "customer@example.com" not in str(captured.value)

    run(scenario())
