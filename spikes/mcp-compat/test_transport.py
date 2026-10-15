"""Real loopback HTTP tests, with separate upstream and proxy listeners."""
import asyncio
from contextlib import asynccontextmanager
import secrets
import socket

import httpx2
from mcp.shared.exceptions import MCPError
import pytest
import uvicorn

from spike import Probe, connect, fixed_app, proxy_app


@asynccontextmanager
async def serve(app):
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='critical', access_log=False))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        async with asyncio.timeout(5):
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError('Server failed to start')
                await asyncio.sleep(.01)
        yield f'http://127.0.0.1:{port}/mcp'
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, 5)
        sock.close()


@pytest.mark.asyncio
async def test_discovery_call_validation_and_request_auth():
    upstream_key, a, b = [secrets.token_urlsafe(32) for _ in range(3)]
    upstream, gateway = Probe(), Probe()
    tokens = {a: 'A', b: 'B'}
    async with serve(fixed_app(upstream_key, upstream)) as origin:
        async with serve(proxy_app(origin, upstream_key, tokens, gateway)) as url:
            async with connect(url, a) as client:
                tools = await client.list_tools()
                assert [tool.name for tool in tools.tools] == ['probe__add']
                result = await client.call_tool('probe__add', {'a': 2, 'b': 3})
                assert not result.is_error and result.structured_content == {'result': 5}
                assert upstream.calls == 1
                for name, args in [('probe__add', {'a': 'bad', 'b': 3}), ('missing', {})]:
                    with pytest.raises(MCPError) as error:
                        await client.call_tool(name, args)
                    assert error.value.code == -32602
                assert upstream.calls == 1
            async def call(key):
                async with connect(url, key) as client:
                    return await client.call_tool('probe__add', {'a': 4, 'b': 5})
            results = await asyncio.gather(call(a), call(b))
            assert all(r.structured_content == {'result': 9} for r in results)
            assert sorted(gateway.actors) == ['A', 'A', 'B']
            async with httpx2.AsyncClient(trust_env=False) as http:
                for method in ['POST', 'GET', 'DELETE']:
                    response = await http.request(method, url, headers={'Authorization': 'Bearer wrong'})
                    assert response.status_code == 401
                assert (await http.post(url)).status_code == 401
                # A gateway key is rejected by upstream: successful proxy calls prove separation.
                assert (await http.post(origin, headers={'Authorization': f'Bearer {a}'})).status_code == 401
                body = {'jsonrpc': '2.0', 'id': 7, 'method': 'tools/list'}
                headers = {'Authorization': f'Bearer {a}', 'Accept': 'application/json, text/event-stream',
                           'MCP-Protocol-Version': '2026-07-28'}
                del tokens[a]
                assert (await http.post(url, headers=headers, json=body)).status_code == 401


@pytest.mark.asyncio
async def test_timeout_returns_sanitized_error_without_retry():
    key, upstream_key = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    upstream = Probe()
    async with serve(fixed_app(upstream_key, upstream, delay=1)) as origin:
        async with serve(proxy_app(origin, upstream_key, {key: 'A'}, Probe(), timeout=.3)) as url:
            async with connect(url, key) as client:
                result = await client.call_tool('probe__add', {'a': 1, 'b': 2})
                assert result.is_error
                assert result.content[0].text == 'Upstream unavailable or timed out; call was not retried.'
                assert upstream.calls == 1
                assert len((await client.list_tools()).tools) == 1


@pytest.mark.asyncio
async def test_listing_survives_upstream_shutdown():
    key, upstream_key = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    upstream = serve(fixed_app(upstream_key, Probe()))
    origin = await upstream.__aenter__()
    try:
        async with serve(proxy_app(origin, upstream_key, {key: 'A'}, Probe())) as url:
            await upstream.__aexit__(None, None, None)
            async with connect(url, key) as client:
                assert len((await client.list_tools()).tools) == 1
                assert (await client.call_tool('probe__add', {'a': 1, 'b': 2})).is_error
    finally:
        await upstream.__aexit__(None, None, None)
