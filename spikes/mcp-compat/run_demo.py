"""Run loopback-only spike; write short-lived client config outside Git."""
import argparse
import asyncio
from contextlib import AsyncExitStack
import json
from pathlib import Path
import secrets
import socket

import uvicorn

from spike import Probe, fixed_app, proxy_app


async def start(app, stack: AsyncExitStack) -> tuple[str, uvicorn.Server, asyncio.Task]:
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    stack.callback(sock.close)
    server = uvicorn.Server(uvicorn.Config(app, log_level='warning', access_log=False))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    async def stop():
        server.should_exit = True
        await asyncio.wait_for(task, 5)
    stack.push_async_callback(stop)
    async with asyncio.timeout(5):
        while not server.started:
            if task.done():
                await task
                raise RuntimeError('Server failed to start')
            await asyncio.sleep(.01)
    return f'http://127.0.0.1:{sock.getsockname()[1]}/mcp', server, task


async def main(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    upstream, gateway = Probe(), Probe()
    key, upstream_key = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    async with AsyncExitStack() as stack:
        origin, _, _ = await start(fixed_app(upstream_key, upstream), stack)
        url, _, _ = await start(proxy_app(origin, upstream_key, {key: 'external-client'}, gateway), stack)
        config = {
            'mcpServers': {
                't002-probe': {
                    'type': 'http',
                    'url': url,
                    'headers': {'Authorization': f'Bearer {key}'},
                }
            }
        }
        path = directory / 'client.secret.json'
        path.touch(mode=0o600)
        path.chmod(0o600)
        path.write_text(json.dumps(config))
        print(f'Gateway: {url}; client config in {directory}; bearer never printed', flush=True)
        try:
            while True:
                await asyncio.sleep(1)
                (directory/'evidence.json').write_text(json.dumps({'upstream_calls': upstream.calls, 'actors': gateway.actors}))
        finally:
            print(f'Stopped; upstream calls: {upstream.calls}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-dir', required=True, type=Path)
    try:
        asyncio.run(main(parser.parse_args().runtime_dir))
    except KeyboardInterrupt:
        pass
