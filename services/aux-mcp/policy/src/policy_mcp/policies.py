from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files


@dataclass(frozen=True)
class PolicyCatalog:
    version: str
    label: str
    policies: dict[str, dict[str, str]]

    def list_policies(self) -> dict[str, object]:
        return {
            "version": self.version,
            "label": self.label,
            "policies": [
                {"topic": topic, "title": policy["title"], "summary": policy["summary"]}
                for topic, policy in sorted(self.policies.items())
            ],
        }

    def get_policy(self, topic: str) -> dict[str, str]:
        normalized = topic.strip().lower()
        policy = self.policies.get(normalized)
        if policy is None:
            supported = ", ".join(sorted(self.policies))
            raise ValueError(f"unsupported policy topic; supported topics: {supported}")
        return {"version": self.version, "label": self.label, "topic": normalized, **policy}

    def collision_fixture(self, search: str | None, page: int, per_page: int) -> dict[str, object]:
        if page < 1 or not 1 <= per_page <= 50:
            raise ValueError("page must be positive and per_page must be between 1 and 50")
        item = {
            "name": "Policy Demo Product Fixture",
            "source": "policy-mcp static collision fixture",
            "label": "Demonstration data - NOT WooCommerce inventory",
        }
        matches = not search or search.strip().lower() in item["name"].lower()
        items = [item] if matches and page == 1 else []
        return {"version": self.version, "items": items[:per_page]}


def load_policies() -> PolicyCatalog:
    payload = json.loads(files("policy_mcp").joinpath("policies.json").read_text())
    return PolicyCatalog(
        version=payload["version"], label=payload["label"], policies=payload["policies"]
    )
