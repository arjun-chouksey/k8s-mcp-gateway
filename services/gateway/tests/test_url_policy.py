import pytest

from app.security.url_policy import validate_upstream_url


ALLOWLIST = (
    "woocommerce-mcp.mcp.svc.cluster.local:8000",
    "currency-mcp.mcp.svc.cluster.local:8000",
    "policy-mcp.mcp.svc.cluster.local:8000",
)


async def resolver(*addresses: str):
    async def resolve(_host: str, _port: int):
        return set(addresses)
    return resolve


@pytest.mark.asyncio
async def test_exact_internal_service_allowlist():
    assert await validate_upstream_url(
        "http://currency-mcp.mcp.svc.cluster.local:8000/mcp", ALLOWLIST,
    ) == "http://currency-mcp.mcp.svc.cluster.local:8000/mcp"
    with pytest.raises(ValueError, match="must use HTTPS"):
        await validate_upstream_url("http://postgres.platform.svc.cluster.local:5432/", ALLOWLIST)
    with pytest.raises(ValueError, match="must use HTTPS"):
        await validate_upstream_url("http://currency-mcp.mcp.svc.cluster.local:8001/mcp", ALLOWLIST)


@pytest.mark.asyncio
async def test_public_https_requires_only_global_resolution():
    public = await resolver("93.184.216.34")
    assert await validate_upstream_url(
        "https://mcp.example.com/mcp", ALLOWLIST, public,
    ) == "https://mcp.example.com/mcp"

    mixed = await resolver("93.184.216.34", "10.0.0.8")
    with pytest.raises(ValueError, match="blocked network"):
        await validate_upstream_url("https://mcp.example.com/mcp", ALLOWLIST, mixed)


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "http://example.com/mcp",
    "https://127.0.0.1/mcp",
    "https://169.254.169.254/latest/meta-data",
    "https://metadata.google.internal/computeMetadata/v1",
    "https://user:password@example.com/mcp",
])
async def test_unsafe_public_targets_are_rejected(url: str):
    public = await resolver("93.184.216.34")
    with pytest.raises(ValueError):
        await validate_upstream_url(url, ALLOWLIST, public)
