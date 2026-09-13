# Demo MCP enforcement service

This is a purpose-built MCP authorization service for the KiroCrew demo, not a LiteLLM implementation. It speaks real Streamable HTTP through the Python MCP SDK, applies a call-time grant, and uses boto3 to make real S3 requests. It can be verified without a model login. That direct verification is separate from observing the actual Crew backend callback.

The service binds only `127.0.0.1:8001`, with the MCP endpoint at `/mcp`. Run it on the same EC2 instance as Crew and its coding backend. The laptop connects to the remote Crew UI; it does not run this service or the coding backend.

## Fixed behavior

| Tool | MCP invocation grant | Fixed S3 key | Intended native demo outcome |
| --- | --- | --- | --- |
| `read_allowed` | Granted | `allowed/sentinel.txt` | Crew approval, MCP grant, successful S3 response |
| `crew_denied` | Granted | `allowed/sentinel.txt` | Crew denies before the MCP service receives the request |
| `mcp_denied` | Denied | No SDK call | Crew approval, then this service rejects the call grant |
| `iam_denied` | Granted | `denied/sentinel.txt` | Crew approval, MCP grant, then S3 denies the role |

All authenticated clients have the fixed principal `kirocrew-demo-client`. Discovery exposes all four harmless tool descriptions; invocation has its own fixed allowlist. This intentionally demonstrates a visible call-time denial. The service does not implement tenant identity, OAuth, group administration, policy synchronization, or LiteLLM's permission semantics.

`crew_denied` is deliberately not rejected by this service. Calling it directly reads the allowed fixture; only the native Crew hook can produce the Crew denial. Do not claim a direct `probe.py` result proves that hook.

Every tool accepts only a `trace_id` (8–80 ASCII letters/digits/underscore/hyphen). Caller input cannot select a bucket, key, API action, role, region, shell command, or URL. Reads are limited to 4 KiB and return a digest and byte count, never object contents. Denials use MCP `isError: true` and structured results identifying the layer.

## Dependencies and local tests

Python 3.12 is used for the accepted local test run. The complete runtime lock is `requirements.txt`; `requirements-test.txt` adds the test dependencies. Both pin hashes. MCP is pinned to `1.30.0` on the supported `<2` maintenance line. Source ranges are in the `.in` files; only update a lock deliberately and rerun the tests. [Official Python SDK v1 documentation](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x)

From this directory:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-test.txt
.venv/bin/python -m pytest -q --junitxml=test-results.xml
```

Tests use the actual MCP SDK HTTP app through an in-process ASGI transport. They start no listening service and make no cloud or model calls. `pytest.ini` places disposable token-test files in the owner-controlled `.pytest-safe-tmp` directory beneath this project, because the token loader correctly rejects Linux's world-writable `/tmp` ancestor. Run tests from a checkout beneath a protected project/home path, not `/tmp`. The fake S3 boundary tests authentication rejection, call-grant denial with no credential lookup, separate handling of S3 AccessDenied, other AWS failures, bounded output, audit failure before dispatch, and host/origin protection. Fake-SDK test results are not live IAM evidence.

## EC2 deployment contract

Provision the service under a separate unprivileged account, with root-owned application code, dependencies and configuration. It needs these settings:

| Setting | Required value |
| --- | --- |
| `DEMO_S3_BUCKET` | Dedicated demo bucket, lowercase letters/digits/hyphens |
| `AWS_REGION` | `us-east-1` |
| `DEMO_MCP_TOKEN_FILE` | Absolute path to the protected service token |
| `AWS_SHARED_CREDENTIALS_FILE` | `/dev/null` is recommended; no static IAM keys belong on EC2 |

Generate the token with `secrets.token_urlsafe(48)` directly into a protected file; never print it, put it in shell arguments, or save it in an evidence receipt. The token must contain 64–256 URL-safe characters. The token loader requires a root-owned regular file, mode `0640` or stricter, and a root-owned directory chain without group/world write permission. Grant file read access only to the service group. Root-provisioned `DEMO_MCP_TOKEN` from a protected systemd `EnvironmentFile` is an alternative; set exactly one token source. The environment form trusts the service manager's file protection because file ownership cannot be established from an environment value.

The runtime uses boto3's default credential chain but rejects static environment keys, shared-credentials files, credential-process providers and missing credentials. Accepted providers are the EC2 instance role and an assume-role profile whose `credential_source` is directly `Ec2InstanceMetadata`. Do not transfer the laptop's IAM credentials. If assuming a dedicated workload role, use a root-protected AWS config with a role ARN and `credential_source = Ec2InstanceMetadata`, without `source_profile`. [AWS EC2 role credentials](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-metadata-security-credentials.html)

Create both tiny fixture objects before rehearsing. Allow `s3:GetObject` only for the allowed object in the demo role and explicitly deny `s3:GetObject` for the denied object. Preserve a provisioning receipt proving that the denied object exists. A missing object can also return 403 when the caller lacks `ListBucket`; the service alone cannot identify which AWS policy caused AccessDenied. An actual AWS response plus the verified object and deployed policy supplies that attribution. [S3 GetObject authorization](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html)

Block the Crew/backend account's access to instance metadata at the OS firewall boundary. Allow only the MCP service and required host-management accounts to use the role. `AWS_EC2_METADATA_DISABLED=true` alone does not prevent direct HTTP access to metadata. Keep service code, token sources, role profiles and firewall policy unwritable to Crew. The MCP bearer token conveys only this demo principal's fixed grants; it is not an AWS credential.

The service entry point is `python server.py` under its virtual environment. Its host and port cannot be overridden. Runtime audit records go to stdout as one JSON object per line for systemd/journald collection; uvicorn access logging is disabled. Audit records include only controlled identifiers, outcome, layer, AWS response request ID, digest and byte count. They omit tokens, credential material, raw AWS exception messages and object contents. Failure to write the pre-dispatch audit stops the call. Failure after an AWS request has begun cannot undo that request and must not be described as prevention.

## Native Crew configuration and session

Install this MCP entry in the dedicated EC2 demo agent's `mcpServers`, and include `@aws-enforcement` in that agent's `tools`. Root should inject the generated token into the configuration securely; the placeholder below is never a usable credential:

```json
{
  "tools": ["@aws-enforcement"],
  "allowedTools": [],
  "mcpServers": {
    "aws-enforcement": {
      "url": "http://127.0.0.1:8001/mcp",
      "headers": {"Authorization": "Bearer <generated-demo-token>"}
    }
  }
}
```

Merge the entry into a dedicated materialized agent; preserve Crew's generated control-plane entries and other required agent fields. Do not add native MCP `autoApprove` or native `allowedTools` grants for these tools. The service also omits read-only annotations to avoid inviting a client-side approval shortcut.

Set the Crew gateway's hooks configuration:

```json
{
  "hooks": {
    "auto_deny_tools": ["@aws-enforcement/crew_denied"],
    "auto_approve_tools": []
  }
}
```

Select the actual Kiro CLI backend, sign in freshly on EC2, and start a new dedicated demo session after configuration changes. Native `kirocrew cloud login` can run the remote device flow. Approve sign-in through the user's own browser session; do not copy the Mac's token store. AWS IAM access does not sign this coding backend in.

Use four separate turns, requesting exactly one tool and a fresh trace identifier each time. Ask the backend not to retry or choose an alternative tool after a denial. A Crew rejection may cancel the rest of a backend turn, so one turn per decision keeps the evidence attributable:

1. Call `read_allowed` with `trace_id=demo-<run>-allow`; approve once through Crew. Expect its digest and an AWS request ID.
2. Call `crew_denied` with `trace_id=demo-<run>-crew`; expect the native Crew block and SEL `hook_deny`, with no matching MCP event.
3. Call `mcp_denied` with `trace_id=demo-<run>-mcp`; approve once through Crew. Expect the service's `tool_grant_denied` and no SDK dispatch.
4. Call `iam_denied` with `trace_id=demo-<run>-iam`; approve once through Crew. Expect AWS `AccessDenied`, HTTP 403 and an AWS request ID.

Capture the actual permission callback, structured tool identity and parameters, Crew session/request ID and SEL result. Map those IDs to the service's trace/invocation IDs and AWS response request IDs. The no-MCP-event assertion depends on complete healthy service logs for the observed interval; log absence alone is not sufficient if collection failed. Store the deployed code, policy and configuration hashes without secret bytes.

The inspected September 12 nightly implementation supporting this procedure is in the workspace snapshot: `dashboard/chat_runner.py:9145` handles native permission events, `:9212` invokes the gate and `:9232` begins its SEL denial path; `hooks.py:1073` matches canonical MCP deny references; `agent.py:1135` describes how native `autoApprove` skips the callback; `acp/session_mcp.py:124` projects HTTP MCP entries; `cli_cloud.py:148` provides fresh remote backend login. Recheck these boundaries if the deployed Crew release differs.

## Direct deployed service verification

After provisioning and starting the service, a trusted operator on EC2 can run this without a model login, using the same protected token source:

```sh
.venv/bin/python probe.py \
  --expected-allowed-sha256 <sha256-from-provisioning-receipt> \
  --receipt /path/to/new-mcp-service-receipt.json
```

The probe checks unauthenticated rejection, the real SDK handshake/catalog, successful `read_allowed` with the provisioned digest, MCP-denied `mcp_denied`, and AWS-denied `iam_denied`. Each result must match its trace/tool/principal and expected success/error flag. STS credential-refresh denial does not count as S3 denial. It makes real S3 calls through the service and refuses to overwrite an existing receipt. It does not call `crew_denied` or claim native Crew verification. The recorded server-file hash identifies the file beside the probe; bind the running service to that code separately through deployment/start evidence. Its URL is fixed to loopback and it disables HTTP environment proxies and redirects. Only run it against the deployed dedicated demo service; the local tests above are the offline alternative.
