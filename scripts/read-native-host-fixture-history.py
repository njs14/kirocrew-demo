#!/usr/bin/env python3
"""Read a recorded 2026-09-13 native slot's named public fixture fields.

Only owner-cookie exchange and a bounded slot GET are used. No WebSocket,
session creation, prompt, approval, policy write or helper execution occurs.
Unrecognized inputs/results are represented by hashes, never printed raw.
The fixed public fixture path, UID and port describe that recorded run; this
is an evidence-recovery utility, not a portable runtime configuration tool.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import quote
from demo_config import load_config, ssh_options

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("host_passive", HERE / "capture-native-client-evidence.py")
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)
native = capture.native
RESULT_FIELDS = {"probe", "authorization_sent", "cookies_sent", "elapsed_ms", "http_status", "native_enforcement_verified",
                 "response_body_read", "application_bytes_sent", "metadata_requested", "connected", "connect_errno", "error"}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def public_input(raw, path):
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict):
        return None
    functional = {key: item for key, item in value.items() if key != "__tool_use_purpose"}
    if functional == {"command": "/usr/bin/python3 " + path}:
        return functional
    if functional == {"operations": [{"mode": "Line", "path": path}]}:
        return functional
    return None


def extract(slot, fixture):
    name = {"anonymous": "anonymous-http.py", "imds": "imds-tcp.py"}[fixture]
    path = "/opt/kirocrew-demo/host-controls/" + name
    expected_source = (HERE.parent / "infrastructure/host-controls" / name).read_text().replace("__EXPECTED_CREW_UID__", "999").replace("__GATEWAY_PORT__", "5476")
    messages = slot.get("messages", [])
    native.require(isinstance(messages, list) and len(messages) <= 100, "slot_history_limit")
    selected, unrecognized = [], []
    for message in messages:
        meta = capture.permission_metadata(message)
        raw = meta.get("input", meta.get("tool_input"))
        if message.get("role") not in {"tool", "permission"} or not meta.get("tool_call_id"):
            continue
        value = public_input(raw, path)
        if value is None:
            unrecognized.append({"tool_call_id": meta["tool_call_id"], "input_sha256": digest(json.dumps(raw, sort_keys=True))})
            continue
        row = {"timestamp": message.get("ts"), "role": message["role"], "tool_call_id": meta["tool_call_id"],
               "input": value, "original_input_sha256": digest(json.dumps(raw, sort_keys=True)), "done": meta.get("done"),
               "kind": meta.get("kind"), "request_id": meta.get("request_id"), "resolved": meta.get("resolved")}
        if isinstance(meta.get("output"), str):
            output = meta["output"]
            row["output_sha256"] = digest(output)
            if output == expected_source.rstrip("\n"):
                row.update(result_type="exact_public_helper_source", source_sha256=digest(expected_source))
            else:
                try:
                    parsed = json.loads(output)
                except ValueError:
                    parsed = None
                expected_probe = {"anonymous": "anonymous_gateway_posture", "imds": "imds_ipv4_tcp_only"}[fixture]
                if isinstance(parsed, dict) and parsed.get("probe") == expected_probe and set(parsed) <= RESULT_FIELDS and all(
                        value is None or isinstance(value, (bool, int)) or (key == "probe" and value == expected_probe) or
                        (key == "error" and value in {"request_failed", "connect_failed"}) for key, value in parsed.items()):
                    row.update(result_type="native_public_helper_output", result=parsed)
                else:
                    row["result_type"] = "unrecognized_output_hash_only"
        selected.append(row)
    return {"fixture": fixture, "path": path, "running": slot.get("running"), "has_more": slot.get("has_more"),
            "next_before": slot.get("next_before"), "total": slot.get("total"), "message_count": len(messages),
            "selected_native_rows": selected, "unrecognized_tool_rows": unrecognized,
            "expected_public_source_sha256": digest(expected_source), "automatic_acceptance": False}


async def read(args):
    import aiohttp
    native.require(bool(capture.SLOT.fullmatch(args.slot)), "invalid_slot")
    config = load_config(args.config)
    native.SSH_OPTIONS = ssh_options(config)
    token = await asyncio.to_thread(native.owner_token, config["ssh"]["admin_alias"])
    base = "http://localhost:" + str(config["ssh"]["local_port"])
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(), trust_env=False,
                                     timeout=aiohttp.ClientTimeout(total=35), headers={"Origin": base}) as http:
        async with http.get(base + "/", params={"token": token}, allow_redirects=False) as response:
            native.require(response.status in (200, 302, 303), "owner_cookie_exchange_failed")
            await capture.bounded_read(response)
        async with http.get(base + "/api/chat/slots/" + quote(args.slot, safe=""), allow_redirects=False) as response:
            native.require(response.status == 200, "slot_read_failed")
            raw = await capture.bounded_read(response)
            slot = json.loads(raw)
    output = extract(slot, args.fixture)
    output.update(kind="read_only_native_public_fixture_history", slot=args.slot, observed_at=native.now(),
                  read_only=True, native_prompt_submitted=False, approval_submitted=False,
                  fixture_scope="Recorded 2026-09-13 fixture path, UID999 and Gateway5476; no assumption about other deployments.",
                  source_response_sha256=hashlib.sha256(raw).hexdigest(), reader_sha256=digest(Path(__file__).read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    native.write_new(args.output, output)
    print(json.dumps({"output": str(args.output), "running": output["running"],
                      "rows": [{key: row.get(key) for key in ("role", "tool_call_id", "done", "result_type", "result")} for row in output["selected_native_rows"]]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/demo.local.json")
    parser.add_argument("--slot", required=True)
    parser.add_argument("--fixture", choices=("anonymous", "imds"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    native.require(not args.output.exists(), "output_already_exists")
    asyncio.run(read(args))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"failed": True, "failure": str(error) if isinstance(error, native.DemoFailure) else type(error).__name__}))
        raise SystemExit(1)
