#!/usr/bin/env python3
import asyncio
import os
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from woo_mcp import OrderFilters, ProductCreate, ProductFilters, WCClient


async def main() -> None:
    async with WCClient(
        base_url=os.environ["WOOCOMMERCE_BASE_URL"],
        oauth_base_url=os.environ["WOOCOMMERCE_OAUTH_BASE_URL"],
        consumer_key=os.environ["WOOCOMMERCE_CONSUMER_KEY"],
        consumer_secret=os.environ["WOOCOMMERCE_CONSUMER_SECRET"],
    ) as client:
        products = await client.list_products(ProductFilters(per_page=5))
        print(f"PASS WCClient product GET ({len(products)} returned)")

        probe = await client.create_product(
            ProductCreate(
                name=f"T-009 WCClient Probe {datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()}",
                regular_price=Decimal("1.00"),
                status="draft",
                virtual=True,
            )
        )
        print(f"PASS WCClient product POST (draft product {probe.id})")

        orders = await client.list_orders(OrderFilters(date="today", per_page=5))
        if orders:
            order = await client.get_order(orders[0].id)
            print(f"PASS WCClient order list/get (order {order.id}, {order.status})")
        else:
            print("PASS WCClient order list (no orders today)")


asyncio.run(main())
