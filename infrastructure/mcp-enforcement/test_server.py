"""In-process protocol and enforcement tests. No model, listening socket, or AWS call."""

import hashlib
import io
import json
import asyncio
import os
from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from starlette.testclient import TestClient

import server

TOKEN = "test-only-" + "x" * 64
SETTINGS = server.Settings(bucket="kirocrew-demo-unit-tests", token=TOKEN)
TRACE = "test-correlation-001"


class FakeS3:
    def __init__(self, error=None, body=b"test fixture, never expose this body"):
        self.calls = []
        self.error = error
        self.body = body
        self.stream = None

    def get_object(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        self.stream = io.BytesIO(self.body)
        return {"Body": self.stream, "ResponseMetadata": {"RequestId": "AWS-REQUEST-123", "HTTPStatusCode": 200}}


def harness(fake=None, audit_write=None):
    records = []
    fake = fake or FakeS3()
    audit = server.JsonAudit(audit_write or records.append)
    creations = []

    def factory():
        creations.append(True)
        return fake

    app = server.build_app(SETTINGS, audit=audit, s3_factory=factory)
    return app, fake, creations, records


def rpc(client, method, params=None, *, headers=None, request_id=1):
    request = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        request["params"] = params
    return client.post("/mcp", json=request, headers=headers or {
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-11-25",
    })


def call(client, name, trace=TRACE):
    response = rpc(client, "tools/call", {"name": name, "arguments": {"trace_id": trace}})
    assert response.status_code == 200, response.text
    return response.json()["result"]


@pytest.mark.parametrize("auth", [None, "Bearer wrong", "Basic " + TOKEN, "Bearer " + TOKEN + "extra"])
def test_missing_or_wrong_auth_never_reaches_sdk(auth):
    app, fake, creations, records = harness()
    headers = {"Accept": "application/json, text/event-stream"}
    if auth:
        headers["Authorization"] = auth
    with TestClient(app, base_url="http://127.0.0.1:8001") as client:
        response = rpc(client, "tools/call", {"name": "read_allowed", "arguments": {"trace_id": TRACE}}, headers=headers)
    assert response.status_code == 401
    assert not fake.calls and not creations
    assert json.loads(records[0])["layer"] == "authentication"
    assert TOKEN not in "\n".join(records)


def test_duplicate_auth_rejected():
    app, fake, creations, _ = harness()
    with TestClient(app, base_url="http://127.0.0.1:8001") as client:
        response = client.post("/mcp", headers=[("Authorization", "Bearer " + TOKEN),
                              ("Authorization", "Bearer " + TOKEN)], json={})
    assert response.status_code == 401
    assert not fake.calls and not creations


def test_mcp_handshake_catalog_and_success_use_real_sdk_transport():
    app, fake, _, records = harness()
    with TestClient(app, base_url="http://127.0.0.1:8001") as client:
        init = rpc(client, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                   "clientInfo": {"name": "demo-test", "version": "1"}})
        assert init.status_code == 200
        assert init.json()["result"]["serverInfo"]["name"] == "KiroCrew demo enforcement"
        catalog = rpc(client, "tools/list").json()["result"]["tools"]
        assert {tool["name"] for tool in catalog} == set(server.TOOL_KEYS)
        assert all(not tool.get("annotations") for tool in catalog)
        result = call(client, "read_allowed")
    payload = result["structuredContent"]
    assert result["isError"] is False
    assert payload["ok"] is True
    assert payload["aws_request_id"] == "AWS-REQUEST-123"
    assert payload["object_sha256"] == hashlib.sha256(fake.body).hexdigest()
    assert fake.calls == [{"Bucket": SETTINGS.bucket, "Key": "allowed/sentinel.txt"}]
    assert fake.stream.closed
    assert fake.body.decode() not in json.dumps(result) + "\n".join(records)
    assert [json.loads(row)["event"] for row in records] == ["tool_decision", "aws_dispatch", "aws_result"]


def test_mcp_call_grant_denial_has_no_credential_lookup_or_sdk_call():
    app, fake, creations, records = harness()
    with TestClient(app, base_url="http://127.0.0.1:8001") as client:
        result = call(client, "mcp_denied")
    payload = result["structuredContent"]
    assert result["isError"] is True
    assert payload["layer"] == "mcp" and payload["error_code"] == "tool_grant_denied"
    assert not fake.calls and not creations
    assert [json.loads(row)["event"] for row in records] == ["tool_decision"]


def test_aws_access_denied_is_actual_client_error_and_separate_from_mcp():
    error = ClientError({"Error": {"Code": "AccessDenied", "Message": "do not leak details/credentials"},
                         "ResponseMetadata": {"HTTPStatusCode": 403, "RequestId": "S3-DENY-123"}}, "GetObject")
    app, fake, creations, records = harness(FakeS3(error))
    with TestClient(app, base_url="http://127.0.0.1:8001") as client:
        result = call(client, "iam_denied")
    payload = result["structuredContent"]
    assert result["isError"] is True
    assert payload["layer"] == "aws" and payload["error_code"] == "AccessDenied"
    assert payload["aws_request_id"] == "S3-DENY-123" and payload["http_status"] == 403
    assert len(creations) == 1 and fake.calls[0]["Key"] == "denied/sentinel.txt"
    assert json.loads(records[-1])["outcome"] == "denied"
    assert "do not leak" not in json.dumps(result) + "\n".join(records)


@pytest.mark.parametrize("error", [
    ClientError({"Error": {"Code": "NoSuchKey"}, "ResponseMetadata": {"HTTPStatusCode": 404}}, "GetObject"),
    ClientError({"Error": {"Code": "ExpiredToken"}, "ResponseMetadata": {"HTTPStatusCode": 403}}, "GetObject"),
    ClientError({"Error": {"Code": "AccessDenied"}, "ResponseMetadata": {"HTTPStatusCode": 403,
                 "RequestId": "STS-REQUEST-123"}}, "AssumeRole"),
    EndpointConnectionError(endpoint_url="https://do-not-log.invalid"),
])
def test_transport_or_other_aws_failure_is_not_iam_denial(error):
    app, _, _, records = harness(FakeS3(error))
    with TestClient(app, base_url="http://127.0.0.1:8001") as client:
        result = call(client, "iam_denied")
    assert result["isError"] is True
    assert result["structuredContent"]["error_code"] != "AccessDenied"
    assert json.loads(records[-1])["outcome"] == "error"
    assert "do-not-log" not in json.dumps(result) + "\n".join(records)


def test_invalid_trace_and_oversized_object_are_bounded():
    app, fake, creations, _ = harness(FakeS3(body=b"x" * 5000))
    with TestClient(app, base_url="http://127.0.0.1:8001") as client:
        invalid = call(client, "read_allowed", trace="bad\ntrace")
        assert invalid["structuredContent"]["error_code"] == "invalid_request"
        assert not creations
        large = call(client, "read_allowed")
    assert large["structuredContent"]["error_code"] == "fixture_too_large"
    assert fake.stream.closed


def test_crew_denied_is_not_fabricated_inside_mcp():
    app, fake, _, _ = harness()
    with TestClient(app, base_url="http://127.0.0.1:8001") as client:
        result = call(client, "crew_denied")
    assert result["structuredContent"]["ok"] is True
    assert len(fake.calls) == 1  # Native Crew must prevent this invocation upstream.


def test_audit_failure_before_dispatch_fails_closed():
    def fail(_):
        raise OSError("do-not-log audit path")
    app, fake, creations, _ = harness(audit_write=fail)
    with TestClient(app, base_url="http://127.0.0.1:8001") as client:
        result = call(client, "read_allowed")
    assert result["structuredContent"]["error_code"] == "service_unavailable"
    assert not creations and not fake.calls


def test_host_and_origin_protection():
    app, fake, creations, _ = harness()
    with TestClient(app, base_url="http://127.0.0.1:8001") as client:
        for headers in [{"Host": "evil.invalid"}, {"Origin": "https://evil.invalid"}]:
            response = rpc(client, "tools/list", headers={"Authorization": "Bearer " + TOKEN,
                            "Accept": "application/json, text/event-stream", **headers})
            assert response.status_code in {400, 421, 403}
    assert not creations and not fake.calls


@pytest.mark.parametrize("method", ["env", "shared-credentials-file", "custom-process", None])
def test_production_factory_refuses_static_or_nonrole_providers(monkeypatch, method):
    session = SimpleNamespace(get_credentials=lambda: SimpleNamespace(method=method) if method else None)
    monkeypatch.setattr(server.boto3, "Session", lambda **kwargs: session)
    with pytest.raises(ValueError, match="instance-role"):
        server.role_s3_client("us-east-1")


def test_assume_role_source_must_be_ec2_metadata(monkeypatch):
    session = SimpleNamespace(get_credentials=lambda: SimpleNamespace(method="assume-role"),
              _session=SimpleNamespace(get_scoped_config=lambda: {"source_profile": "static-user"}))
    monkeypatch.setattr(server.boto3, "Session", lambda **kwargs: session)
    with pytest.raises(ValueError, match="sourced directly"):
        server.role_s3_client("us-east-1")


@pytest.mark.parametrize("mode,accepted", [(0o600, True), (0o640, True), (0o644, False),
                                          (0o660, False), (0o650, False)])
def test_token_file_permissions_with_real_files(tmp_path, mode, accepted):
    path = tmp_path / "token"
    path.write_text(TOKEN + "\n")
    path.chmod(mode)
    if accepted:
        assert server.read_protected_token(path, owner_uid=os.getuid()) == TOKEN
    else:
        with pytest.raises(ValueError):
            server.read_protected_token(path, owner_uid=os.getuid())


def test_token_rejects_writable_ancestor_and_leaf_symlink(tmp_path):
    path = tmp_path / "token"
    path.write_text(TOKEN)
    path.chmod(0o600)
    tmp_path.chmod(0o777)
    try:
        with pytest.raises(ValueError, match="directory chain"):
            server.read_protected_token(path, owner_uid=os.getuid())
    finally:
        tmp_path.chmod(0o700)
    link = tmp_path / "token-link"
    link.symlink_to(path)
    with pytest.raises(OSError):
        server.read_protected_token(link, owner_uid=os.getuid())


def test_token_rejects_wrong_owner(tmp_path, monkeypatch):
    path = tmp_path / "token"
    path.write_text(TOKEN)
    path.chmod(0o600)
    real_fstat = os.fstat

    def wrong_owner(fd):
        info = real_fstat(fd)
        return SimpleNamespace(st_uid=os.getuid() + 1, st_mode=info.st_mode, st_size=info.st_size)

    monkeypatch.setattr(server.os, "fstat", wrong_owner)
    with pytest.raises(ValueError, match="root-owned"):
        server.read_protected_token(path, owner_uid=os.getuid())


@pytest.mark.parametrize("correct_digest", [True, False])
def test_direct_probe_uses_sdk_client_and_requires_provisioned_digest(monkeypatch, correct_digest):
    import httpx
    import probe

    class ConditionalS3(FakeS3):
        def get_object(self, **kwargs):
            if kwargs["Key"].startswith("denied/"):
                self.calls.append(kwargs)
                raise ClientError({"Error": {"Code": "AccessDenied"}, "ResponseMetadata": {
                    "HTTPStatusCode": 403, "RequestId": "REAL-BOUNDARY-FAKE-123"}}, "GetObject")
            return super().get_object(**kwargs)

    app, fake, _, _ = harness(ConditionalS3())
    real_client = httpx.AsyncClient

    def in_process_client(**kwargs):
        return real_client(transport=httpx.ASGITransport(app=app), **kwargs)

    monkeypatch.setattr(probe.httpx, "AsyncClient", in_process_client)

    async def run():
        async with app.router.lifespan_context(app):
            digest = hashlib.sha256(fake.body).hexdigest() if correct_digest else "0" * 64
            return await probe.verify(TOKEN, digest)

    receipt = asyncio.run(run())
    assert receipt["passed"] is correct_digest
    assert receipt["native_crew_backend_verified"] is False
    assert len(fake.calls) == 2
    assert "crew_denied" not in {row["name"] for row in receipt["checks"]}
    assert TOKEN not in json.dumps(receipt)
