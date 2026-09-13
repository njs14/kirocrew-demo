"""Verify an already-running local MCP service with the real MCP SDK, without a model.

This makes real S3 requests when the target service uses its production provider.
It does not start a service, provision AWS resources, or claim native backend proof.
"""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from server import token_from_environment

URL = "http://127.0.0.1:8001/mcp"


async def verify(token, expected_allowed_sha256):
    if not re.fullmatch(r"[a-f0-9]{64}", expected_allowed_sha256):
        raise ValueError("Expected fixture SHA must be 64 lowercase hexadecimal characters")
    prefix = "probe-" + uuid.uuid4().hex
    receipt = {"schema": 1, "time": datetime.now(timezone.utc).isoformat(),
               "kind": "direct_mcp_service_probe", "native_crew_backend_verified": False,
               "url": URL, "trace_prefix": prefix, "checks": [],
               "dependencies": {name: importlib.metadata.version(name) for name in ["mcp", "boto3", "httpx"]},
               "expected_allowed_sha256": expected_allowed_sha256,
               "server_file_sha256": hashlib.sha256(Path(__file__).with_name("server.py").read_bytes()).hexdigest()}
    async with httpx.AsyncClient(timeout=20, trust_env=False, follow_redirects=False) as anonymous:
        response = await anonymous.post(URL, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        receipt["checks"].append({"name": "authentication_required", "passed": response.status_code == 401,
                                  "http_status": response.status_code})
    async with httpx.AsyncClient(headers={"Authorization": "Bearer " + token}, timeout=30,
                                 trust_env=False, follow_redirects=False) as http:
        async with streamable_http_client(URL, http_client=http) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                catalog = await session.list_tools()
                names = {tool.name for tool in catalog.tools}
                receipt["checks"].append({"name": "catalog", "passed": names == {
                    "read_allowed", "crew_denied", "mcp_denied", "iam_denied"}, "tools": sorted(names)})
                for name, layer, code, expected_error in [
                    ("read_allowed", "aws", None, False),
                    ("mcp_denied", "mcp", "tool_grant_denied", True),
                    ("iam_denied", "aws", "AccessDenied", True),
                ]:
                    trace_id = prefix + "-" + name
                    result = await session.call_tool(name, {"trace_id": trace_id})
                    payload = result.structuredContent or {}
                    passed = (result.isError == expected_error and payload.get("layer") == layer
                              and payload.get("error_code") == code
                              and payload.get("ok") is (not expected_error)
                              and payload.get("tool") == name and payload.get("trace_id") == trace_id
                              and payload.get("principal") == "kirocrew-demo-client"
                              and bool(payload.get("invocation_id")))
                    if name == "read_allowed":
                        passed = (passed and payload.get("object_sha256") == expected_allowed_sha256
                                  and isinstance(payload.get("object_bytes"), int)
                                  and 0 <= payload["object_bytes"] <= 4096)
                    if name in {"read_allowed", "iam_denied"}:
                        passed = passed and bool(payload.get("aws_request_id"))
                    if name == "iam_denied":
                        passed = passed and payload.get("http_status") == 403
                    receipt["checks"].append({"name": name, "passed": passed, "result": payload})
    receipt["passed"] = all(check["passed"] for check in receipt["checks"])
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-allowed-sha256", required=True,
                        help="SHA256 of the allowed sentinel from its provisioning receipt")
    parser.add_argument("--receipt", type=Path, help="Write a new receipt; refuses to overwrite an existing path")
    args = parser.parse_args()
    try:
        receipt = asyncio.run(verify(token_from_environment(), args.expected_allowed_sha256))
    except Exception as exc:
        # Network/SDK exception strings can contain request headers or local file paths.
        receipt = {"kind": "direct_mcp_service_probe", "passed": False,
                   "native_crew_backend_verified": False, "error_type": type(exc).__name__}
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        with args.receipt.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
    print(rendered, end="")
    raise SystemExit(0 if receipt["passed"] else 1)


if __name__ == "__main__":
    main()
