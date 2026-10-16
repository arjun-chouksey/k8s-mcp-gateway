from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import httpx
from oauthlib.oauth1 import Client as OAuth1Client
from oauthlib.oauth1 import SIGNATURE_HMAC_SHA256, SIGNATURE_TYPE_QUERY
from pydantic import BaseModel, ValidationError

from .models import (
    OrderDetail,
    OrderFilters,
    OrderStatus,
    OrderSummary,
    ProductCreate,
    ProductFilters,
    ProductSummary,
)


class WCClientError(RuntimeError):
    pass


class WCAuthenticationError(WCClientError):
    pass


class WCValidationError(WCClientError):
    pass


class WCNotFoundError(WCClientError):
    pass


class WCTimeoutError(WCClientError):
    pass


class WCUncertainWriteError(WCClientError):
    pass


class WCUpstreamError(WCClientError):
    pass


class WCClient:
    def __init__(
        self,
        *,
        base_url: str,
        oauth_base_url: str,
        consumer_key: str,
        consumer_secret: str,
        store_timezone: str = "Asia/Kolkata",
        timeout: httpx.Timeout | float = httpx.Timeout(20.0, connect=3.0),
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._oauth_base_url = oauth_base_url.rstrip("/")
        self._timezone = ZoneInfo(store_timezone)
        self._oauth = OAuth1Client(
            consumer_key,
            client_secret=consumer_secret,
            signature_method=SIGNATURE_HMAC_SHA256,
            signature_type=SIGNATURE_TYPE_QUERY,
        )
        self._http = httpx.AsyncClient(timeout=timeout, transport=transport)

    async def __aenter__(self) -> WCClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def list_products(self, filters: ProductFilters) -> list[ProductSummary]:
        payload = await self._request("GET", "/wp-json/wc/v3/products", params=filters.model_dump(exclude_none=True))
        return [self._validate_model(ProductSummary, item) for item in self._expect_list(payload)]

    async def create_product(self, product: ProductCreate) -> ProductSummary:
        payload = await self._request(
            "POST",
            "/wp-json/wc/v3/products",
            json_body=product.model_dump(mode="json", exclude_none=True),
            write=True,
        )
        return self._validate_model(ProductSummary, self._expect_mapping(payload))

    async def list_orders(self, filters: OrderFilters) -> list[OrderSummary]:
        payload = await self._request(
            "GET", "/wp-json/wc/v3/orders", params=filters.query(self._timezone)
        )
        return [self._validate_model(OrderSummary, item) for item in self._expect_list(payload)]

    async def get_order(self, order_id: int) -> OrderDetail:
        self._validate_id(order_id)
        payload = await self._request("GET", f"/wp-json/wc/v3/orders/{order_id}")
        return self._validate_model(OrderDetail, self._expect_mapping(payload))

    async def update_order_status(self, order_id: int, status: OrderStatus) -> OrderDetail:
        self._validate_id(order_id)
        payload = await self._request(
            "PUT",
            f"/wp-json/wc/v3/orders/{order_id}",
            json_body={"status": status.value},
            write=True,
        )
        return self._validate_model(OrderDetail, self._expect_mapping(payload))

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
        write: bool = False,
    ) -> Any:
        request_url = f"{self._base_url}{path}"
        canonical_url = f"{self._oauth_base_url}{path}"
        if params:
            canonical_url = str(httpx.URL(canonical_url, params=params))
        body = None if json_body is None else json.dumps(json_body, separators=(",", ":"))
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        signed_url, signed_headers, _ = self._oauth.sign(
            canonical_url,
            http_method=method,
            body=body,
            headers=headers,
        )
        canonical_parts = urlsplit(signed_url)
        request_parts = urlsplit(request_url)
        final_url = urlunsplit(
            (request_parts.scheme, request_parts.netloc, request_parts.path, canonical_parts.query, "")
        )
        try:
            response = await self._http.request(
                method, final_url, content=body, headers=dict(signed_headers)
            )
        except httpx.TimeoutException as error:
            if write:
                raise WCUncertainWriteError(
                    "WooCommerce write timed out; its outcome is unknown and was not retried"
                ) from error
            raise WCTimeoutError("WooCommerce read timed out") from error
        except httpx.RequestError as error:
            if write:
                raise WCUncertainWriteError(
                    "WooCommerce write connection failed; its outcome is unknown and was not retried"
                ) from error
            raise WCUpstreamError("WooCommerce is unreachable") from error

        if response.status_code >= 400:
            self._raise_http_error(response)
        try:
            return response.json()
        except ValueError as error:
            raise WCUpstreamError("WooCommerce returned an invalid JSON response") from error

    @staticmethod
    def _raise_http_error(response: httpx.Response) -> None:
        code = "unknown_error"
        try:
            body = response.json()
            if isinstance(body, dict) and isinstance(body.get("code"), str):
                code = body["code"][:100]
        except ValueError:
            pass
        message = f"WooCommerce request failed ({response.status_code}, {code})"
        if response.status_code in (401, 403):
            raise WCAuthenticationError(message)
        if response.status_code == 404:
            raise WCNotFoundError(message)
        if response.status_code in (400, 409, 422):
            raise WCValidationError(message)
        raise WCUpstreamError(message)

    @staticmethod
    def _expect_mapping(payload: Any) -> Mapping[str, Any]:
        if not isinstance(payload, Mapping):
            raise WCUpstreamError("WooCommerce returned an unexpected response shape")
        return payload

    @staticmethod
    def _expect_list(payload: Any) -> list[Mapping[str, Any]]:
        if not isinstance(payload, list) or not all(isinstance(item, Mapping) for item in payload):
            raise WCUpstreamError("WooCommerce returned an unexpected response shape")
        return payload

    @staticmethod
    def _validate_id(value: int) -> None:
        if isinstance(value, bool) or value <= 0:
            raise WCValidationError("WooCommerce resource ID must be a positive integer")

    @staticmethod
    def _validate_model(model: type[BaseModel], payload: Mapping[str, Any]) -> Any:
        try:
            return model.model_validate(payload)
        except ValidationError as error:
            raise WCUpstreamError("WooCommerce returned an invalid response shape") from error
