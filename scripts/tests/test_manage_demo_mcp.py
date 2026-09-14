"""Guardrails for the same-product MCP registration and hook transition."""
import copy
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("managed_mcp", Path(__file__).parents[1] / "manage-demo-mcp.py")
mcp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mcp)


def agent():
    return {"name": "enforcement-demo", "allowedTools": [], "mcpServers": {mcp.NAME: {
        "url": "http://127.0.0.1:8001/mcp", "headers": {"Authorization": "Bearer " + "x" * 48}}}}


def policy():
    return {"has_policy": True, "unavailable": False,
            "distribution": {"configured": True, "source_scheme": "file", "on_unavailable": "fail_closed", "error_code": ""},
            "scopes": [{"scope": "mcp", "governed": True, "source": "policy"}]}


class ManagedMcpTests(unittest.TestCase):
    def test_spec_uses_existing_remote_loopback_only(self):
        expected = agent()["mcpServers"][mcp.NAME]
        self.assertEqual(mcp.demo_spec(agent()), expected)
        for url in ("https://example.com/mcp", "http://localhost:8001/mcp", "http://127.0.0.1:8001/mcp?token=x",
                    "http://user@127.0.0.1:8001/mcp", "http://127.0.0.1:8001/other"):
            value = agent()
            value["mcpServers"][mcp.NAME]["url"] = url
            with self.assertRaises(ValueError):
                mcp.demo_spec(value)

    def test_header_and_auto_approve_injection_refused(self):
        for patch in ({"autoApprove": ["*"]}, {"command": "sh"}, {"headers": {"Authorization": "Bearer x\r\nX: y"}}):
            value = agent()
            value["mcpServers"][mcp.NAME].update(patch)
            with self.assertRaises(ValueError):
                mcp.demo_spec(value)
        value = agent()
        value["allowedTools"] = ["@aws-enforcement/*"]
        with self.assertRaisesRegex(ValueError, "auto_approval"):
            mcp.demo_spec(value)

    def test_add_and_idempotent_registration(self):
        spec = mcp.demo_spec(agent())
        self.assertEqual(mcp.registration_state({}, {}, [{}, {}], spec), "add")
        store = {"mcpServers": {mcp.NAME: spec, "unrelated": {"command": "echo"}}}
        self.assertEqual(mcp.registration_state(store, {"mcpServers": {mcp.NAME: spec}}, [{}, {}], spec), "already_registered")
        self.assertEqual(store["mcpServers"]["unrelated"], {"command": "echo"})

    def test_global_collision_never_imported_or_overwritten(self):
        spec = mcp.demo_spec(agent())
        with self.assertRaisesRegex(ValueError, "global_name_collision"):
            mcp.registration_state({}, {}, [{"mcpServers": {mcp.NAME: spec}}, {}], spec)

    def test_materialized_only_collision_refused(self):
        spec = mcp.demo_spec(agent())
        with self.assertRaisesRegex(ValueError, "materialized_name_collision"):
            mcp.registration_state({}, {"mcpServers": {mcp.NAME: spec}}, [{}, {}], spec)

    def test_crew_name_collision_refused(self):
        spec = mcp.demo_spec(agent())
        with self.assertRaisesRegex(ValueError, "crew_entry_collision"):
            mcp.registration_state({"mcpServers": {mcp.NAME: {"command": "evil"}}}, {}, [{}, {}], spec)

    def test_disabled_entry_never_reenabled(self):
        spec = mcp.demo_spec(agent())
        with self.assertRaisesRegex(ValueError, "disabled"):
            mcp.registration_state({"mcpServers": {mcp.NAME: {**spec, "disabled": True}}}, {}, [{}, {}], spec)

    def test_materialized_auto_approve_refused(self):
        spec = mcp.demo_spec(agent())
        store = {"mcpServers": {mcp.NAME: spec}}
        for emitted in ({"mcpServers": {mcp.NAME: {**spec, "autoApprove": ["*"]}}},
                        {"mcpServers": {mcp.NAME: spec}, "allowedTools": ["@aws-enforcement"]}):
            with self.assertRaises(ValueError):
                mcp.registration_state(store, emitted, [{}, {}], spec)

    def test_retirement_preserves_all_other_fields_and_input(self):
        original = {"hooks": {"auto_deny_tools": ["first", mcp.DENY, "last"], "custom": {"x": 1}},
                    "dashboard": {"terminal": {"enabled": False}}, "unknown_user_value": [1, 2]}
        before = copy.deepcopy(original)
        after = mcp.retired_config(original)
        self.assertEqual(original, before)
        expected = copy.deepcopy(original)
        expected["hooks"]["auto_deny_tools"] = ["first", "last"]
        self.assertEqual(after, expected)

    def test_similar_hook_not_retired(self):
        original = {"hooks": {"auto_deny_tools": ["@aws-enforcement/crew_denied_*", "@aws-enforcement/*"]}}
        self.assertEqual(mcp.retired_config(original), original)

    def test_ambiguous_mutable_list_refused(self):
        for value in ([mcp.DENY, mcp.DENY], [False], "*"):
            with self.assertRaises(ValueError):
                mcp.retired_config({"hooks": {"auto_deny_tools": value}})

    def test_no_or_unavailable_policy_cannot_retire(self):
        for patch in ({"has_policy": False}, {"unavailable": True}, {"scopes": []}):
            with self.assertRaises(ValueError):
                mcp.policy_posture({**policy(), **patch})

    def test_profile_only_or_noncentral_policy_cannot_retire(self):
        for source in ("profile", "ungoverned"):
            value = policy()
            value["scopes"][0]["source"] = source
            with self.assertRaises(ValueError):
                mcp.policy_posture(value)
        for patch in ({"configured": False}, {"source_scheme": "https"}, {"on_unavailable": "continue"}, {"error_code": "misconfigured"}):
            value = policy()
            value["distribution"].update(patch)
            with self.assertRaises(ValueError):
                mcp.policy_posture(value)

    def test_stale_plan_refuses_before_post_or_hook_retirement(self):
        class Response:
            status = 302
            async def __aenter__(self):
                return self
            async def __aexit__(self, *_):
                pass
            async def read(self, *_):
                return b""
            @property
            def content(self):
                return self
        class Session(Response):
            def get(self, *_args, **_kwargs):
                return Response()
        aio = SimpleNamespace(ClientSession=lambda **_: Session(), CookieJar=lambda: None,
                              ClientTimeout=lambda **_: None)
        request = {"port": 5476, "owner_helper": "/helper", "state_dir": "/state", "service": "demo.service",
                   "deployment": {"stack": "fixture"}, "helper_sha256": "new-source", "action": "apply",
                   "retire_mutable_deny": True, "apply": True, "expected": {"stale": True}}
        objects = {"config": {"hooks": {"auto_deny_tools": [mcp.DENY]}}}
        called = []
        async def api(_http, method, url, **_kwargs):
            called.append(method)
            return policy()
        with patch.dict("sys.modules", {"aiohttp": aio}), patch.object(mcp.os, "geteuid", return_value=0), \
             patch.object(mcp.sys, "platform", "linux"), patch.object(mcp.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=999)), \
             patch.object(mcp.importlib.util, "find_spec", return_value=SimpleNamespace(origin="/runtime/kiro_crew/__init__.py")), \
             patch.object(mcp, "owner_session_token", return_value="private-not-output"), \
             patch.object(mcp, "policy_proof", return_value={"policy_sha256": "new-policy"}), \
             patch.object(mcp, "inventory", return_value=({}, objects, {"config": "changed"}, mcp.demo_spec(agent()), "add")), \
             patch.object(mcp, "http_json", side_effect=api), patch.object(mcp, "retire_hook") as retire:
            with self.assertRaisesRegex(ValueError, "exact_prior_plan_required"):
                asyncio.run(mcp.operate(request))
            self.assertEqual(called, ["GET"])
            retire.assert_not_called()

    def test_duplicate_json_keys_refused(self):
        with self.assertRaisesRegex(ValueError, "duplicate_json_key"):
            mcp.decode('{"mcpServers":{},"mcpServers":{"attacker":{}}}')

    def test_unsafe_absolute_paths_refused(self):
        for path in ("relative", "/etc/../tmp/x", "/etc/./x", "/etc/x;id", "/etc/x\ny"):
            with self.assertRaises(ValueError):
                mcp.absolute(path)


if __name__ == "__main__":
    unittest.main()
