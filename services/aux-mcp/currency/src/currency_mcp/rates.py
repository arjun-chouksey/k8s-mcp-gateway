from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from importlib.resources import files


@dataclass(frozen=True)
class DemoRates:
    version: str
    label: str
    base_currency: str
    rates_per_inr: dict[str, Decimal]

    def convert(self, amount: Decimal, from_currency: str, to_currency: str) -> dict[str, str]:
        if not amount.is_finite() or amount < 0:
            raise ValueError("amount must be a finite non-negative decimal")
        source = from_currency.strip().upper()
        target = to_currency.strip().upper()
        if source not in self.rates_per_inr or target not in self.rates_per_inr:
            supported = ", ".join(sorted(self.rates_per_inr))
            raise ValueError(f"unsupported currency; supported currencies: {supported}")
        rate = self.rates_per_inr[target] / self.rates_per_inr[source]
        converted = amount * rate
        return {
            "amount": format(amount, "f"),
            "from_currency": source,
            "to_currency": target,
            "rate": format(rate, "f"),
            "converted_amount": format(converted, "f"),
            "rate_version": self.version,
            "rate_label": self.label,
        }

    def metadata(self) -> dict[str, object]:
        return {
            "version": self.version,
            "label": self.label,
            "base_currency": self.base_currency,
            "rates_per_inr": {
                code: format(rate, "f") for code, rate in sorted(self.rates_per_inr.items())
            },
        }


def load_rates() -> DemoRates:
    payload = json.loads(files("currency_mcp").joinpath("rates.json").read_text())
    rates = {code: Decimal(value) for code, value in payload["rates_per_inr"].items()}
    if payload["base_currency"] != "INR" or rates.get("INR") != Decimal("1"):
        raise RuntimeError("demo rate file must use INR with rate 1 as its base")
    if "NOT live FX" not in payload["label"]:
        raise RuntimeError("demo rate label must explicitly state NOT live FX")
    return DemoRates(
        version=payload["version"],
        label=payload["label"],
        base_currency=payload["base_currency"],
        rates_per_inr=rates,
    )
