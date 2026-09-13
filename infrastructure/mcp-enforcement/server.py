"""Purpose-built demo MCP authorization service; not a LiteLLM implementation."""

from __future__ import annotations

import asyncio
import contextvars
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import boto3
import uvicorn
from botocore.config import Config as AwsConfig
from botocore.exceptions import BotoCoreError, ClientError
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent
from starlette.responses import JSONResponse

PRINCIPAL = "kirocrew-demo-client"
TOOL_KEYS = {
    "read_allowed": "allowed/sentinel.txt",
    "crew_denied": "allowed/sentinel.txt",
    "mcp_denied": "allowed/sentinel.txt",
    "iam_denied": "denied/sentinel.txt",
}
# Discovery of the fixed catalog is permitted; these are INVOCATION grants.
CALL_GRANTS = frozenset({"read_allowed", "crew_denied", "iam_denied"})
MAX_OBJECT_BYTES = 4096
_principal: contextvars.ContextVar[str | None] = contextvars.ContextVar("principal", default=None)
_trace_pattern = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{7,79}\Z")
_request_pattern = re.compile(r"[A-Za-z0-9_+/=-]{1,256}\Z")


def validate_token(token: str) -> str:
    # Generate with secrets.token_urlsafe(48): 64 URL-safe characters / 384 bits.
    # Length is a shape check, not proof of how much entropy an operator used.
    if not re.fullmatch(r"[A-Za-z0-9_-]{64,256}", token):
        raise ValueError("MCP token must contain 64-256 URL-safe characters")
    return token


def token_from_environment() -> str:
    file_name = os.environ.get("DEMO_MCP_TOKEN_FILE")
    inline = os.environ.get("DEMO_MCP_TOKEN")
    if bool(file_name) == bool(inline):
        raise ValueError("Set exactly one of DEMO_MCP_TOKEN_FILE or DEMO_MCP_TOKEN")
    return read_protected_token(Path(file_name)) if file_name else validate_token(inline or "")


def read_protected_token(path: Path, *, owner_uid: int = 0) -> str:
    """Refuse writable ancestors, symlinks, broad read permissions, and nonowners."""
    path = path.absolute()
    for parent in reversed(path.parents):
        info = parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, owner_uid}
                or info.st_mode & 0o022):
            raise ValueError("Token directory chain must be owner-controlled and not group/world writable")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != owner_uid
                or info.st_mode & 0o137 or info.st_size > 257):
            raise ValueError("Token file must be root-owned, regular, and mode 0640 or stricter")
        with os.fdopen(fd, "r", encoding="ascii", closefd=False) as stream:
            return validate_token(stream.read(258).strip())
    finally:
        os.close(fd)


@dataclass(frozen=True)
class Settings:
    bucket: str
    token: str = field(repr=False)
    region: str = "us-east-1"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", self.bucket):
            raise ValueError("DEMO_S3_BUCKET must name a demo bucket using lowercase letters, digits, and hyphens")
        validate_token(self.token)
        if self.region != "us-east-1":
            raise ValueError("This demo is restricted to us-east-1")

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(bucket=os.environ.get("DEMO_S3_BUCKET", ""), token=token_from_environment(),
                   region=os.environ.get("AWS_REGION", "us-east-1"))


class JsonAudit:
    """Emit one allowlisted JSON record per event; never serialize raw requests/errors."""

    def __init__(self, write: Callable[[str], Any] | None = None):
        self._write = write or self._stdout
        self._lock = threading.Lock()

    @staticmethod
    def _stdout(line: str) -> None:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()

    def emit(self, event: str, **fields: Any) -> None:
        allowed = {"trace_id", "invocation_id", "principal", "tool", "layer", "outcome",
                   "aws_request_id", "http_status", "error_code", "object_bytes", "object_sha256"}
        if fields.keys() - allowed:
            raise ValueError("Unexpected audit fields")
        record = {"time": datetime.now(timezone.utc).isoformat(), "service": "demo-mcp-enforcement",
                  "event": event, **fields}
        with self._lock:
            self._write(json.dumps(record, sort_keys=True, separators=(",", ":")))


def role_s3_client(region: str):
    session = boto3.Session(region_name=region)
    credentials = session.get_credentials()
    # A deployment may use an assume-role profile with credential_source=Ec2InstanceMetadata.
    # Never accept copied static keys or a local credentials file in this service.
    if credentials is None or credentials.method not in {"iam-role", "assume-role"}:
        raise ValueError("Service requires EC2 instance-role or assume-role credentials")
    if credentials.method == "assume-role":
        profile = session._session.get_scoped_config()
        if profile.get("credential_source") != "Ec2InstanceMetadata" or profile.get("source_profile"):
            raise ValueError("Assume-role must be sourced directly from EC2 instance metadata")
    return session.client("s3", config=AwsConfig(
        region_name=region, connect_timeout=5, read_timeout=10,
        retries={"total_max_attempts": 1}, user_agent_extra="KiroCrewEnforcementDemo/1.0"))


def _aws_request_id(response: dict[str, Any]) -> str | None:
    value = response.get("ResponseMetadata", {}).get("RequestId")
    return value if isinstance(value, str) and _request_pattern.fullmatch(value) else None


class Enforcement:
    def __init__(self, settings: Settings, audit: JsonAudit, s3_factory: Callable[[], Any]):
        self.settings, self.audit, self.s3_factory = settings, audit, s3_factory

    def invoke(self, tool: str, trace_id: str, principal: str | None) -> dict[str, Any]:
        if tool not in TOOL_KEYS or not _trace_pattern.fullmatch(trace_id):
            self.audit.emit("tool_decision", layer="request", outcome="denied", error_code="invalid_request")
            return {"ok": False, "layer": "request", "error_code": "invalid_request"}
        base = {"trace_id": trace_id, "invocation_id": str(uuid.uuid4()), "tool": tool,
                "principal": PRINCIPAL if principal == PRINCIPAL else "unauthenticated"}
        if principal != PRINCIPAL:
            self.audit.emit("tool_decision", **base, layer="authentication", outcome="denied")
            return {"ok": False, **base, "layer": "authentication", "error_code": "unauthorized"}
        if tool not in CALL_GRANTS:
            self.audit.emit("tool_decision", **base, layer="mcp", outcome="denied")
            return {"ok": False, **base, "layer": "mcp", "error_code": "tool_grant_denied"}

        # Audit must succeed before constructing credentials or dispatching any SDK call.
        self.audit.emit("tool_decision", **base, layer="mcp", outcome="allowed")
        try:
            s3 = self.s3_factory()
            self.audit.emit("aws_dispatch", **base, layer="aws", outcome="attempted")
            response = s3.get_object(Bucket=self.settings.bucket, Key=TOOL_KEYS[tool])
        except ClientError as exc:
            request_id = _aws_request_id(exc.response)
            metadata = exc.response.get("ResponseMetadata", {})
            status = metadata.get("HTTPStatusCode")
            code = exc.response.get("Error", {}).get("Code", "")
            # Role refresh may raise STS AccessDenied while boto3 signs GetObject.
            # That is credential failure, not a completed S3 authorization test.
            is_s3 = exc.operation_name == "GetObject"
            denied = is_s3 and code in {"AccessDenied", "AccessDeniedException"} and status == 403
            # Neither a timeout, a missing object, nor another 403 is reported as IAM proof.
            result = {"ok": False, **base, "layer": "aws", "aws_request_id": request_id,
                      "http_status": status if isinstance(status, int) else None,
                      "error_code": "AccessDenied" if denied else (
                          "aws_client_error" if is_s3 else "aws_credential_error")}
            self.audit.emit("aws_result", **base, layer="aws", outcome="denied" if denied else "error",
                            aws_request_id=result["aws_request_id"], http_status=result["http_status"],
                            error_code=result["error_code"])
            return result
        except (BotoCoreError, ValueError):
            self.audit.emit("aws_result", **base, layer="aws", outcome="error", error_code="aws_unavailable")
            return {"ok": False, **base, "layer": "aws", "error_code": "aws_unavailable"}

        request_id = _aws_request_id(response)
        body = response["Body"]
        try:
            # Read only the configured small fixture. Content never enters output or logs.
            content = body.read(MAX_OBJECT_BYTES + 1)
            if len(content) > MAX_OBJECT_BYTES:
                self.audit.emit("aws_result", **base, layer="aws", outcome="error",
                                aws_request_id=request_id, error_code="fixture_too_large")
                return {"ok": False, **base, "layer": "aws", "error_code": "fixture_too_large",
                        "aws_request_id": request_id}
        finally:
            body.close()
        digest = hashlib.sha256(content).hexdigest()
        self.audit.emit("aws_result", **base, layer="aws", outcome="allowed", aws_request_id=request_id,
                        object_bytes=len(content), object_sha256=digest)
        return {"ok": True, **base, "layer": "aws", "aws_request_id": request_id,
                "object_bytes": len(content), "object_sha256": digest}


class BearerAuth:
    def __init__(self, app: Any, expected_token: str, audit: JsonAudit):
        self.app, self.token, self.audit = app, expected_token.encode("ascii"), audit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        values = [value for key, value in scope.get("headers", ()) if key.lower() == b"authorization"]
        parts = values[0].split(b" ", 1) if len(values) == 1 else []
        valid = (len(parts) == 2 and parts[0].lower() == b"bearer"
                 and secrets.compare_digest(parts[1], self.token))
        if not valid:
            try:
                self.audit.emit("authentication", layer="authentication", outcome="denied")
            except Exception:
                await JSONResponse({"error": "audit_unavailable"}, status_code=503)(scope, receive, send)
                return
            await JSONResponse({"error": "unauthorized"}, status_code=401,
                               headers={"WWW-Authenticate": 'Bearer realm="kirocrew-demo"'})(scope, receive, send)
            return
        marker = _principal.set(PRINCIPAL)
        try:
            await self.app(scope, receive, send)
        finally:
            _principal.reset(marker)


def build_app(settings: Settings, *, audit: JsonAudit | None = None,
              s3_factory: Callable[[], Any] | None = None):
    audit = audit or JsonAudit()
    enforcement = Enforcement(settings, audit, s3_factory or (lambda: role_s3_client(settings.region)))
    mcp = FastMCP("KiroCrew demo enforcement", host="127.0.0.1", port=8001,
                  stateless_http=True, json_response=True, max_request_body_size=16384,
                  transport_security=TransportSecuritySettings(
                      enable_dns_rebinding_protection=True,
                      allowed_hosts=["127.0.0.1:8001", "localhost:8001"], allowed_origins=[]))

    def add_tool(name: str, description: str) -> None:
        async def call(trace_id: str) -> CallToolResult:
            try:
                result = await asyncio.to_thread(enforcement.invoke, name, trace_id, _principal.get())
            except Exception:
                # Do not surface credential-provider errors, raw SDK exception text, or configuration paths.
                result = {"ok": False, "layer": "service", "error_code": "service_unavailable"}
            return CallToolResult(isError=not result["ok"], structuredContent=result,
                                  content=[TextContent(type="text", text=json.dumps(result, sort_keys=True))])
        # No read-only annotation: demonstrate the backend's permission callback,
        # without inviting a client-side annotation-based approval shortcut.
        mcp.tool(name=name, description=description)(call)

    add_tool("read_allowed", "Read the fixed allowed S3 demo fixture; return only its digest and AWS request ID.")
    add_tool("crew_denied", "Harmless fixed S3 fixture read that the native Crew hook must block before MCP dispatch.")
    add_tool("mcp_denied", "Request a fixed S3 fixture read without a call grant; this service rejects it before AWS.")
    add_tool("iam_denied", "Read the fixed existing S3 fixture that the deployed demo IAM role explicitly denies.")
    app = mcp.streamable_http_app()
    app.add_middleware(BearerAuth, expected_token=settings.token, audit=audit)
    return app


def main() -> None:
    settings = Settings.from_environment()
    # Deliberately no host/port override or reload mode for this demo deployment.
    uvicorn.run(build_app(settings), host="127.0.0.1", port=8001, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
