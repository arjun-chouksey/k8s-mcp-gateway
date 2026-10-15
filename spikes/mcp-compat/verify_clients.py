"""Run the two required real-client checks against loopback HTTP servers."""
from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
import importlib.metadata
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
from typing import Any

from run_demo import start
from spike import Probe, fixed_app, proxy_app


ROOT = Path(__file__).resolve().parent
INSPECTOR = ROOT / "node_modules/.bin/mcp-inspector"


def run(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        env=env,
        stdin=subprocess.DEVNULL,
        text=True,
    )


def json_output(process: subprocess.CompletedProcess[str], client: str) -> dict[str, Any]:
    if process.returncode != 0:
        raise RuntimeError(f"{client} failed ({process.returncode}): {process.stderr.strip()}")
    return json.loads(process.stdout)


async def main() -> None:
    codex = shutil.which("codex")
    if codex is None:
        raise RuntimeError("Codex CLI is not installed or not on PATH")
    if not INSPECTOR.is_file():
        raise RuntimeError("Run npm ci in spikes/mcp-compat before this check")

    upstream_key, gateway_key = (secrets.token_urlsafe(32) for _ in range(2))
    upstream_probe, gateway_probe = Probe(), Probe()

    async with AsyncExitStack() as stack:
        upstream_url, _, _ = await start(fixed_app(upstream_key, upstream_probe), stack)
        gateway_url, _, _ = await start(
            proxy_app(
                upstream_url,
                upstream_key,
                {gateway_key: "external-client"},
                gateway_probe,
            ),
            stack,
        )

        with tempfile.TemporaryDirectory(prefix="k8s-t002-") as temp:
            config_path = Path(temp) / "inspector.secret.json"
            config_path.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "t002-probe": {
                                "type": "http",
                                "url": gateway_url,
                                "headers": {"Authorization": f"Bearer {gateway_key}"},
                            }
                        }
                    }
                )
            )
            config_path.chmod(0o600)

            inspector_base = [
                str(INSPECTOR),
                "--cli",
                "--config",
                str(config_path),
                "--server",
                "t002-probe",
                "--format",
                "json",
            ]
            listed = json_output(
                await asyncio.to_thread(run, inspector_base + ["--method", "tools/list"]),
                "MCP Inspector tools/list",
            )
            assert [tool["name"] for tool in listed["result"]["tools"]] == ["probe__add"]

            called = json_output(
                await asyncio.to_thread(
                    run,
                    inspector_base
                    + [
                        "--method",
                        "tools/call",
                        "--tool-name",
                        "probe__add",
                        "--tool-args-json",
                        '{"a":20,"b":22}',
                    ],
                ),
                "MCP Inspector tools/call",
            )
            assert called["result"]["structuredContent"] == {"result": 42}
            assert called["result"]["isError"] is False

            rejected = await asyncio.to_thread(
                run,
                [
                    str(INSPECTOR),
                    "--cli",
                    gateway_url,
                    "--method",
                    "tools/list",
                    "--header",
                    "Authorization: Bearer deliberately-wrong",
                    "--protocol-era",
                    "modern",
                    "--stored-auth-only",
                    "--format",
                    "json",
                ],
            )
            assert rejected.returncode == 3
            assert "HTTP 401" in rejected.stderr

            codex_env = os.environ.copy()
            codex_env["T002_MCP_TOKEN"] = gateway_key
            codex_result = await asyncio.to_thread(
                run,
                [
                    codex,
                    "exec",
                    "--ephemeral",
                    "--ignore-user-config",
                    "--skip-git-repo-check",
                    "-C",
                    temp,
                    "-s",
                    "read-only",
                    "--json",
                    "-c",
                    f'mcp_servers.t002probe.url="{gateway_url}"',
                    "-c",
                    'mcp_servers.t002probe.bearer_token_env_var="T002_MCP_TOKEN"',
                    "-c",
                    'mcp_servers.t002probe.enabled_tools=["probe__add"]',
                    "-c",
                    'mcp_servers.t002probe.default_tools_approval_mode="approve"',
                    "Use the t002probe MCP tool probe__add exactly once with a=19 and b=23. "
                    "Return only RESULT=<number>.",
                ],
                env=codex_env,
            )
            if codex_result.returncode != 0:
                raise RuntimeError(
                    f"Codex CLI failed ({codex_result.returncode}): {codex_result.stderr.strip()}"
                )
            events = [json.loads(line) for line in codex_result.stdout.splitlines() if line.startswith("{")]
            calls = [
                event["item"]
                for event in events
                if event.get("type") == "item.completed"
                and event.get("item", {}).get("type") == "mcp_tool_call"
            ]
            assert len(calls) == 1
            assert calls[0]["server"] == "t002probe"
            assert calls[0]["tool"] == "probe__add"
            assert calls[0]["arguments"] == {"a": 19, "b": 23}
            assert calls[0]["error"] is None
            assert calls[0]["result"]["structured_content"] == {"result": 42}

    assert upstream_probe.calls == 2
    assert gateway_probe.actors == ["external-client", "external-client"]
    print(
        json.dumps(
            {
                "codex": run([codex, "--version"]).stdout.strip(),
                "inspector": run([str(INSPECTOR), "--version"]).stdout.strip(),
                "mcp_python_sdk": importlib.metadata.version("mcp"),
                "proxied_calls": upstream_probe.calls,
                "result": "PASS",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
