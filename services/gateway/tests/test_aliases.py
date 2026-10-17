import pytest

from app.mcp_gateway.aliases import public_alias


def test_alias_is_deterministic_and_collision_safe_across_slugs():
    assert public_alias("woo", "list_products") == "woo__list_products"
    assert public_alias("policy", "list_products") == "policy__list_products"


@pytest.mark.parametrize("name", ["", "contains space", "x" * 129, "bad/name"])
def test_malformed_upstream_tool_name_is_rejected(name):
    with pytest.raises(ValueError, match="tool name"):
        public_alias("woo", name)
