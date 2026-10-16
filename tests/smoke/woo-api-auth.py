#!/usr/bin/env python3
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = os.environ["WOOCOMMERCE_BASE_URL"].rstrip("/")
OAUTH_BASE_URL = os.environ["WOOCOMMERCE_OAUTH_BASE_URL"].rstrip("/")
CONSUMER_KEY = os.environ["WOOCOMMERCE_CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["WOOCOMMERCE_CONSUMER_SECRET"]
API_URL = f"{BASE_URL}/wp-json/wc/v3/products"


def percent_encode(value: str) -> str:
    return urllib.parse.quote(str(value), safe="~-._")


def request(method: str, url: str, *, query=None, body=None, authenticated=True):
    query = dict(query or {})
    if authenticated:
        query.update(
            {
                "oauth_consumer_key": CONSUMER_KEY,
                "oauth_nonce": secrets.token_hex(16),
                "oauth_signature_method": "HMAC-SHA256",
                "oauth_timestamp": str(int(time.time())),
            }
        )
        normalized = "&".join(
            f"{percent_encode(key)}={percent_encode(value)}"
            for key, value in sorted(query.items())
        )
        oauth_url = OAUTH_BASE_URL + url.removeprefix(BASE_URL)
        signature_base = "&".join(
            (method.upper(), percent_encode(oauth_url), percent_encode(normalized))
        )
        signing_key = f"{percent_encode(CONSUMER_SECRET)}&".encode()
        digest = hmac.new(signing_key, signature_base.encode(), hashlib.sha256).digest()
        query["oauth_signature"] = base64.b64encode(digest).decode()

    request_url = f"{url}?{urllib.parse.urlencode(query)}" if query else url
    payload = None if body is None else json.dumps(body).encode()
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(request_url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        try:
            response_body = json.load(error)
        except (json.JSONDecodeError, UnicodeDecodeError):
            response_body = {}
        return error.code, response_body


anonymous_status, _ = request(
    "GET", API_URL, query={"per_page": 1}, authenticated=False
)
if anonymous_status not in (401, 403):
    raise SystemExit(f"anonymous product request unexpectedly returned {anonymous_status}")
print(f"PASS anonymous product request denied ({anonymous_status})")

get_status, products = request("GET", API_URL, query={"per_page": 1})
if get_status != 200 or not isinstance(products, list):
    raise SystemExit(f"authenticated product GET failed ({get_status})")
print("PASS OAuth 1.0a authenticated product GET (200)")

probe_sku = f"t008-auth-probe-{int(time.time())}"
post_status, product = request(
    "POST",
    API_URL,
    body={
        "name": "T-008 REST Auth Probe",
        "type": "simple",
        "status": "draft",
        "regular_price": "1.00",
        "virtual": True,
        "sku": probe_sku,
    },
)
if post_status != 201 or not isinstance(product.get("id"), int):
    raise SystemExit(f"authenticated product POST failed ({post_status})")
print(f"PASS OAuth 1.0a authenticated product POST (201), draft product {product['id']}")
