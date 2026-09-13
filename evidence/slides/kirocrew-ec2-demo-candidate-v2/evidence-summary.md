# Evidence for the EC2 deck candidate

This packet accompanies a nine-slide deck for an audience with senior AWS and IAM knowledge. The desktop client and AWS deployment are real. Native Kiro CLI authentication is still in progress. The deck must distinguish completed direct MCP/AWS checks from the pending native backend sequence.

The sources below are local observations and saved API responses gathered on September 13, 2026 UTC. The council can assess how accurately the deck presents this supplied evidence. It cannot independently establish the current cloud state from this packet alone.

## Deployed environment

- CloudFormation stack creation completed in `us-east-1`.
- One `t3a.small` uses Ubuntu 24.04 amd64, 2 vCPU and 2 GiB RAM. CPU credits use standard mode.
- It uses an existing public subnet and an ephemeral public IPv4 address. No NAT gateway or load balancer was created.
- The security group has exactly one ingress rule: TCP 22 from the current client IPv4 `/32`. It has no public Gateway or MCP ingress and no IPv6 ingress. Public client and server addresses are omitted from this review packet.
- Gateway binds to remote `127.0.0.1:5476`. The purpose-built demo MCP service binds to remote `127.0.0.1:8001/mcp`.
- The laptop has an SSH forward from `127.0.0.1:5599` to the remote Gateway. Host-key verification binds to the authenticated EC2 console fingerprint.
- The root EBS volume is encrypted, 24 GiB gp3 and deleted when the instance terminates.
- The S3 bucket blocks public access, uses bucket-owner-enforced ownership and AES256 encryption, and denies non-TLS access. CloudFormation retains the bucket and its TLS-only policy on stack deletion.
- CloudFormation `CREATE_COMPLETE` is separate from host bootstrap success. The bootstrap-complete marker and active Gateway/MCP services were observed on the instance.

Sources: `infrastructure/ec2-demo.json`, `evidence/aws/stack-state.json`, `evidence/aws/security-group.json`, `evidence/aws/route-preflight.json`, `evidence/aws/ssh-verification.json`, `evidence/aws/ec2-console-bootstrap.json`.

## Desktop and installed baseline

- Native KiroCrew Nightly UI shows window `Kiro Crew [:5599]`, status `Gateway connected`, agent `enforcement-demo` and project `/srv/kirocrew-demo/workspace`.
- Local `runLocalGateway` is false. Runtime inspection found no local port 5476 listener and found SSH listening on port 5599.
- The installed Mac package identifies `0.7.0-nightly.20260912t060850`. Selected source files match its distribution RECORD, and a broader package snapshot exists.
- The EC2 Crew runtime is a custom Linux repack of that frozen package with Linux dependencies and native libraries. It is not an official Linux nightly artifact. No source commit is claimed for it.
- The custom repack archive SHA256 is `5133df99766a436a0fe346c6c57b4475fa00389a62fe7e464ec8440942e33d39`.
- Linux Python dependencies use exact versions and accepted artifact hashes. The installer permits binary distributions only.
- Kiro CLI `2.21.4` came from its official stable Linux artifact and matched its manifest. CLI archive SHA256: `a7a3c727796582e2d9132a38170e6e82a5296f0bdfbda68c38ffeef7b199382d`.
- Native backend authentication and a model-backed session remain unverified in this candidate. The earlier Builder ID device flow looped in the browser. The current attempt uses the user's known GitHub provider without transferring login state or credentials from another product.
- The UI reports low memory, with about 1.2 GB free on the 2 GiB host. Full-session performance and sandbox behavior remain unverified.

Sources: `evidence/aws/client-runtime-verification.json`, `evidence/nightly/installed-nightly-verification.json`, `evidence/aws/linux-repack.json`, `infrastructure/crew-requirements-linux.lock`, `evidence/aws/kiro-cli-artifact.json`.

## Host and credential boundaries

- Root owns code and service definitions. `crew` runs the Gateway, backend and remote workspace. `mcp-demo` runs the MCP service as a separate UID.
- The Gateway requires an owner-based firewall guard that rejects the `crew` UID's access to both EC2 metadata addresses. A live metadata request as `crew` failed. IMDSv2 is required, metadata IPv6 is disabled, and the response hop limit is one.
- The MCP process uses the default AWS SDK credential chain and accepts only instance-role credentials from IMDS, or an assumed role sourced from IMDS. No IAM user keys were copied to EC2.
- The instance role permits `s3:GetObject` under the fixed `allowed/*` and `denied/*` prefixes, with an explicit deny under `denied/*`. It also has the SSM core managed policy.
- A fixed bearer principal and four fixed tools make this a demonstration authorization service. It is not a deployed LiteLLM gateway or a multiuser OAuth/RBAC service.
- The principal's grant allows `read_allowed`, `crew_denied` and `iam_denied`. It denies `mcp_denied` at call time even though all four tools appear in discovery.
- Every tool takes only a bounded ASCII `trace_id`. Bucket and object keys are fixed. Tools cannot accept arbitrary AWS APIs, commands or URLs. Successful reads return only byte count and digest.
- The Crew agent exposes only this MCP server, has no preapproved tools and uses interactive approval. Crew config lists `@aws-enforcement/crew_denied` in its automatic deny rules.
- Crew configuration is service-user-owned. This demo does not establish an immutable, centrally managed policy floor or isolation against root.

Sources: `infrastructure/bootstrap.sh`, `infrastructure/configure-demo.py`, `infrastructure/kirocrew-demo.service`, `infrastructure/kirocrew-mcp-demo.service`, `infrastructure/mcp-enforcement/server.py`, `evidence/aws/iam-demo-policy.json`.

## Observed direct MCP and AWS results

Receipt type: `direct_mcp_service_probe`. Timestamp: `2026-09-13T04:17:07Z`. Overall passed: true. Native Crew backend verified: false.

| Check | Observed result |
| --- | --- |
| Unauthenticated request | HTTP 401 |
| Tool discovery | All four expected tools |
| `read_allowed` | Success, 55 bytes, SHA256 `34ebbefeb5f66527fbc80083c3b695a63e675c2093fd5f3f079a7c5bfe4b9160`, AWS request ID `NJ47PCKDNPWNT29P` |
| `mcp_denied` | `tool_grant_denied`, with no AWS dispatch for that trace |
| `iam_denied` | S3 `AccessDenied`, HTTP 403, AWS request ID `NJ428FX3JS4EV6VK` |

The denied object existed before the test, independently verified through the provisioning principal. An STS failure is explicitly excluded from the implementation's S3 IAM-denial proof. Thirty service tests passed, covering MCP HTTP behavior and bounded AWS fakes. These tests do not establish the native Crew callback path.

The native `crew_denied` call must stop automatically before MCP dispatch to count as Crew prevention. A presenter rejecting a permission prompt is not evidence of that configured deny. The later native sequence must correlate backend execution, Crew records, MCP audit and AWS outcomes by trace ID.

Sources: `evidence/aws/mcp-live-receipt.json`, `evidence/aws/mcp-live-audit.jsonl`, `evidence/aws/seed-fixtures-result.json`, `infrastructure/mcp-enforcement/TEST-RECEIPT.json`.

## Pricing and cleanup

- AWS Pricing API: Linux `t3a.small` On Demand in `us-east-1`, $0.0188 per hour.
- AWS VPC pricing: $0.005 per public IPv4 hour.
- Combined running compute and IPv4: $0.0238 per hour, rounded to $0.024 on the slide.
- AWS Pricing API: gp3 in `us-east-1`, $0.08 per GB-month. 24 GiB costs $1.92 per month.
- At 730 running hours, compute, IPv4 and EBS total $19.294, rounded to about $19 per month. S3, transfer, model usage and taxes are additional.
- Stopping releases the ephemeral public IPv4 and stops compute billing. EBS persists and remains billable. Refresh the SSH target after restart.
- Stack deletion removes the instance and root volume but retains S3. The retained bucket requires explicit cleanup.

Sources: `evidence/aws/t3a-small-pricing.json`, `evidence/aws/gp3-pricing.json`, <https://aws.amazon.com/vpc/pricing/>, `infrastructure/ec2-demo.json`.

## Visual and historical boundaries

- Slide 2 preserves the accepted single endpoint-control enclosure as a reference control map. The screenshot has not been altered. It does not prove deployment of every pictured enterprise control.
- The new EC2 topology keeps one execution enclosure. The presentation derivative changes only the root SVG viewBox and dimensions to omit exterior whitespace and the generic color legend. All diagram child bytes remain identical to the canonical export.
- The accepted source-linked diagram baseline is September 11. The installed runtime is the separately fingerprinted September 12 nightly. No older source SHA is assigned to the newer package.
- The earlier synthetic demo produced seven valid SEL events and detected a modified record. It did not execute a model backend or cloud request and must remain separate from the new EC2 receipts.
- Primary AWS MCP in `us-east-1` handled provisioning. The old AWS Knowledge plugin was removed. The provisioning connector and purpose-built EC2 demo MCP service are separate tools.
- Central policy distribution, external SEL collection, universal coverage, EDR enrollment and multiuser MCP identity remain outside demonstrated scope.

Sources: `HANDOFF.md`, `evidence/browser/endpoint-slide.png`, `evidence/aws/archify/presentation-crop.json`, `evidence/nightly/baseline-verification.json`, `CONTINUATION-RECEIPT.json`, `evidence/aws/primary-mcp-tools.json`.
