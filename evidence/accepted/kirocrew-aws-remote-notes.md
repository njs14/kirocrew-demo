# KiroCrew endpoint protection and governance layers

Verified nightly retained. The current nightly feed could not be refreshed during this edit. Build: `0.7.0.dev20260911060948`; commit `fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482`.

The updated visual has three tabs: **Security layers**, **AWS deployment**, and **Controls & demo proof**. The AWS view retains its service icons. The security view groups endpoint control into one host panel: an enterprise protection band, the managed runtime, the policy ceiling, six L0–L5 rows, and cross-cutting controls. Four outside actors keep entry identity, central policy, MCP governance and target authorization distinct.

The diagram shows control relationships, not a guaranteed chronological pipeline. A backend may execute a tool without sending a Crew permission request, and an event observed after execution cannot prevent that action. Managed configuration attempts to close gate-skipping paths where supported; prove the actual behavior on the demo host.

## E · Managed endpoint baseline

Owner: Enterprise. Scope: All processes on the execution host.

MDM and EDR where supported, managed OS configuration, disk encryption, device identity, restricted administration and network egress establish the host baseline.

These are enterprise controls. Crew is not an endpoint detection and response product. Protect the machine where execution happens; a remote Crew service does not govern independently launched laptop agents.

Demo: Name the execution host and show its management, identity and network posture.

## L0 · OS sandbox

Owner: Crew + OS. Scope: Agent subprocess tree and descendants.

The sandbox wrapper confines agent processes using platform-native facilities. Linux and macOS have different implementations; credential-path visibility and environment handling are part of the launch boundary. A policy floor can require a minimum sandbox level.

Inspect the effective launch posture for the exact OS and backend. Configuration, native backend sandbox ownership, unavailable facilities and explicit unconfined allowances affect the result. VM isolation is a separate outer boundary.

Demo: Show the effective sandbox mode and one harmless denied access from inside the agent process.

Sources: [sandbox.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/sandbox.py), [platform/governance.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/platform/governance.py)

## L1 · Filesystem and protected configuration

Owner: Crew. Scope: Tool requests that reach the path gate.

Resolved-path checks protect sensitive reads and writes. A wider write-protected set covers configuration. Keystone files include policy and trust records that the agent must not be able to rewrite to authorize itself.

Path checks mediate known file/tool paths. Shell, imported executables and independent host processes need OS-level confinement as well. A privileged host operator remains outside the agent threat boundary.

Demo: Attempt a read of a synthetic protected path, then an attempted change to a protected policy or trust record.

Sources: [security/paths.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/security/paths.py), [hooks.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/hooks.py), [platform/governance.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/platform/governance.py)

## L2 · Commands and exfiltration shapes

Owner: Crew. Scope: PreToolUse decisions over actual tool arguments.

The command gate evaluates denied operations, shell command forms and exfiltration checks before trust or approval shortcuts at that gate. Enterprise command pins and companion additions constrain operator-configurable rules.

Built-in denied rules are default-on but configurable; do not describe the entire shipped catalog as an immutable floor. Suspicious bash patterns in the history scan are advisory, a different control from execution blocking.

Demo: Use a harmless command shaped to match a known enabled deny rule and show the rule and decision.

Sources: [security/denied_rules.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/security/denied_rules.py), [security/exfil.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/security/exfil.py), [platform/security_authority.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/platform/security_authority.py), [hooks.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/hooks.py)

## L3 · Input and response validation

Owner: Crew. Scope: Registered MCP schemas and API boundaries.

Registered schemas enforce types, bounded lengths, enum choices and normalization. Responses can be sanitized and truncated to limit oversized or malformed inputs and outputs.

Coverage is per tool. In this nightly, some dispatchers pass unregistered tools to their handler without central schema validation; the computer-use dispatcher rejects unregistered tools. Validation is not authorization.

Demo: Submit malformed arguments to a known schema-backed tool and show rejection before its handler runs.

Sources: [validation.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/validation.py), [security_posture.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/security_posture.py)

## L4 · Output redaction

Owner: Crew. Scope: Covered human-facing and external output sinks.

Credential-pattern scanners, exfiltration-URL checks and streaming redaction reduce sensitive output at registered sinks. The posture registry identifies concrete coverage instead of a fixed marketing count.

Pattern recognition is not general-purpose DLP and cannot guarantee detection of arbitrary secrets, encodings or semantic leakage. Coverage varies by sink; transport and downstream data controls remain necessary.

Demo: Use fake credentials and a synthetic exfiltration URL; show the redacted result without handling real secrets.

Sources: [security/redaction.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/security/redaction.py), [security/exfil.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/security/exfil.py), [security_posture.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/security_posture.py)

## L5 · Security Event Log

Owner: Crew + enterprise collector. Scope: Recorded security decisions and activity.

SEL stores structured events with an HMAC integrity chain. Its signing material is separated from the log directory, and rotated segments remain individually verifiable.

A valid chain does not prove complete event capture, immutable retention or resistance to a fully privileged host compromise. Collector integration and external retention are separate deployment work. SSM port forwarding does not record tool payloads.

Demo: Correlate a denied action with its SEL event, run verification, and identify what reaches the external collector.

Sources: [sel.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/sel.py), [security_posture.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/security_posture.py)

## G · Policy and profile governance

Owner: Crew. Scope: Cross-cutting ceiling and narrower session scopes.

Effective permissions compose Policy ∩ Profile. Profiles bind to relevant surfaces, apps or tasks and may narrow the policy ceiling. Scopes cover tools, MCP, commands, paths, channels, approval posture, sandbox floors, backend selection and capabilities.

A policy declaration is meaningful only where its enforcer is connected. Backend admission and live session retirement are different operations. The presence of a governance scope alone does not prove a remote integration is deployed.

Demo: Show policy explain for the same operation under two profiles and identify the limiting rule.

Sources: [platform/governance.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/platform/governance.py), [platform/governance_profiles.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/platform/governance_profiles.py), [agent_backend_governance.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/agent_backend_governance.py)

## A · Access and surface controls

Owner: Crew + access provider. Scope: Browser, dashboard, messaging and remote transport.

Dashboard token authentication, origin/CSRF checks and Host validation protect the browser-facing boundary. Messaging surfaces apply their own owner, user and origin checks. SSH/SSM or MicroVM endpoint authentication protects a separate transport boundary.

Authorization to open a tunnel or port does not automatically become per-user Crew authorization or permission to call downstream tools. A logical conversation session is not necessarily a separate OS process.

Demo: Show the entry identity, Crew session identity and downstream workload identity as three separate facts.

Sources: [security_posture.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/security_posture.py), [messaging/session_trust.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/messaging/session_trust.py)

## P · Approvals and backend enforcement

Owner: Crew + selected backend. Scope: Permission callbacks and pre-tool hooks.

Crew brokers approval decisions for requests that reach its boundary. Its hard path, command and governance decisions precede approval/trust shortcuts there. Managed backend configuration also removes unsafe gate-skipping approval entries where applicable.

Native backend auto-approval can execute without a Crew permission callback. An observational tool event received after execution is not a prevention point. Rehearse enforcement with the actual backend, version and launch settings.

Demo: Demonstrate allow, ask and deny on the chosen backend, then explain which event occurs before execution.

Sources: [hooks.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/hooks.py), [platform/governance.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/platform/governance.py)

## C · Credentials and environment

Owner: Crew + OS + IAM. Scope: Process launch and service authority.

Launch handling scrubs sensitive inherited environment variables and sandbox policy limits access to credential locations. Internal credential access follows explicit privileged paths. External MCP services should use narrowly scoped workload identities.

A per-session IAM role is still usable by code that can obtain its credentials. An unprivileged Unix user does not by itself isolate an EC2 instance profile. Do not put control-plane or broad target-system authority in the agent environment.

Demo: Inspect environment names and role permissions without printing credential values.

Sources: [sandbox.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/sandbox.py), [hooks.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/hooks.py), [security/paths.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/security/paths.py)

## R · Resource protection

Owner: Crew + OS + cloud runtime. Scope: Process, memory and descriptor usage.

Launch wrappers can apply Linux cgroup process/memory bounds and resource limits. Cloud compute sizing, runtime ceilings and task termination add separate outer limits.

Availability and strength are platform dependent. Resource bounds reduce exhaustion; they do not authorize a tool operation or guarantee that a provider billing budget is enforced.

Demo: Show configured limits and the effective host mechanism; use a small controlled resource exercise.

Sources: [sandbox.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/sandbox.py)

## T · Project skill trust and agent context

Owner: Crew + operator. Scope: Project-supplied skills, memory and steering.

Project skill loading has a consent record tied to the canonical project directory, stored in the protected trust area. Memory, steering, lessons and skills then supply context to the selected backend.

Consenting to load a skill is not proof its instructions are safe. Skills, plans and memory are not ACLs; prompt injection remains a reason to enforce the lower execution layers.

Demo: Open an untrusted sample project and show the project-skill trust decision.

Sources: [skill_trust.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/skill_trust.py)

## X · Apps, hooks and unattended work

Owner: Crew. Scope: Gateway services and extension capabilities.

App manifests declare permissions checked at installation and runtime. Governance capabilities cover script hooks, spawning, memory writes, browsing, cron, messaging and other extensions. These constrain the Gateway services that keep work running.

A workflow, scheduler or subagent does not automatically create a new host isolation boundary. Each dispatch path and extension must honor the applicable permissions and runtime controls.

Demo: Show one disabled capability and an app permission declaration, then a blocked attempt through that path.

Sources: [apps/permissions.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/apps/permissions.py), [hooks.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/hooks.py), [platform/governance.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/platform/governance.py)

## M · MCP and target-service governance

Owner: External + Crew. Scope: Routed remote calls and target APIs.

Crew governs known MCP references where its checks apply. A separately deployed LiteLLM/MCP tier can add caller authentication, server/tool grants and service credentials; target AWS IAM or SaaS authorization then decides whether the resource action is allowed.

The proposed external gateway governs only traffic routed through it. Direct shell/SDK/network access needs separate confinement. Caller OAuth identity and downstream AWS workload credentials are not interchangeable.

Demo: Demonstrate gateway tool denial separately from downstream IAM denial.

Sources: [platform/governance.py](https://github.com/kirodotdev/KiroCrew/blob/fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482/src/kiro_crew/platform/governance.py)

## AWS deployment and MicroVM alternative

The existing EC2 + SSM diagram is included in the second tab. It remains a proposal, including the S3-to-protected-file policy sync and optional LiteLLM/MCP tier.

For a MicroVM alternative, place Crew Gateway, backend and workspace together inside each session VM. Add a session broker outside it. Public authenticated ingress, the eight-hour lifetime including suspension, durable state and safe run/resume hooks must be addressed. VPC egress is not private ingress. This integration has not been tested.

[MicroVM lifecycle](https://docs.aws.amazon.com/lambda/latest/dg/microvms-launching.html) · [Networking](https://docs.aws.amazon.com/lambda/latest/dg/microvms-networking.html)

## Validation

Both embedded diagrams passed all nine Archify showcase artifact checks. The viewer preserves their HTML as embedded documents. Static light and dark previews were reviewed by the author and a subagent. The review found no blocking issues; its minor legend inconsistency was corrected by removing the redundant generic legend. Chromium was unavailable, so full browser behavior and responsive containment remain unverified. The wrapper is a separate integration artifact, not itself an Archify single-diagram deliver receipt.

## Original AWS walkthrough

# KiroCrew remote Gateway on AWS

Use this proposed AWS deployment view after the logical governance diagram. The demo starts with an IAM-authorized SSM tunnel to a private EC2 host. The host runs the KiroCrew Gateway, selected coding backend, workspace and session state. The optional MCP tier is a separate deployment to prove tool authorization and downstream IAM independently.

This is an architecture proposal, not a deployed environment. It retains the previously researched KiroCrew nightly `0.7.0.dev20260911060948`, commit `fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482`. It does not assert that this remains the latest nightly on September 12. AWS documentation was checked September 12, 2026.

## Component and control mapping

| Component | What to demonstrate | Boundary or dependency |
|---|---|---|
| Workstation + Session Manager | A federated human role can start a port-forward session to the approved instance | IAM tunnel access does not automatically create per-user Crew identity or tool permissions |
| Private EC2 + SSM Agent | Loopback Gateway, no public IP, no inbound EC2 ports | SSM Agent initiates outbound connections; the diagram shows logical session flow, not inbound TCP initiation |
| PrivateLink endpoints | Instance-side `ssm` and `ssmmessages` connectivity | Enable private DNS; endpoint security groups allow HTTPS from the instance; legacy `ec2messages` requirements vary by Region and agent |
| Narrow EC2 instance profile | SSM management, selected S3 reads and log writes | A Unix user boundary alone does not isolate instance-profile credentials from agent processes |
| S3 policy artifacts | Publish a versioned policy and observe Crew refresh | Proposed privileged sync reads S3 through a gateway endpoint and writes a protected `file://` source; not native S3 support |
| EBS | Persistent workspace, state and local logs | Encrypted attached storage, not a routed network service; KMS key permissions and backup policy need deployment configuration |
| Optional ECS / Fargate MCP tier | LiteLLM tool grants, MCP execution, downstream IAM denial | Use separate tasks and task roles as appropriate; MCP caller OAuth identity is separate from AWS workload credentials |
| Controlled egress | Approved provider connection and blocked destination | Network Firewall rules and symmetric routing provide enforcement; NAT provides translation. Other external MCP traffic needs equivalent controls |
| CloudWatch Logs | Selected application and OS evidence | Collectors, permissions, retention and log coverage must be configured; a Logs interface endpoint permits private delivery |
| CloudTrail | Who started or ended the SSM session | Session Manager port-forwarded payload is not recorded; tool evidence comes from application logs |

The private-subnet box groups endpoint and compute placement. It is not one shared security group: use separate groups for the SSM endpoints, EC2 host and MCP tasks. The egress box abbreviates firewall-subnet and public-NAT routing. EBS is AZ-scoped storage. S3, CloudWatch, Systems Manager and IAM are managed AWS services, not resources with private-subnet IPs.

## Policy wiring

The pinned nightly supports `KIROCREW_POLICY_URL=file://...` as a refreshed distribution source. Neither the file nor an ancestor directory may be writable by the Crew process. A root-owned sync process can download a policy with IAM and atomically publish it under a protected directory while Crew runs unprivileged. That sync process is proposed integration work.

`KIROCREW_SECURITY_POLICY` is a separate local policy read at boot; do not present it as the same periodic distribution mechanism. Backend permission enforcement depends on the supported hooks and settings. A remote Gateway governs its own execution host; independent laptop coding agents are outside this remote service.

## Suggested live sequence

1. **20 seconds — locate execution.** Trace workstation → SSM → private EC2. State that the agent and workspace are on the server.
2. **40 seconds — prove access control.** Show no public IP or inbound SSH rule, the scoped human IAM grant, and an established SSM port-forward session.
3. **60 seconds — show a supported policy decision.** Run an allowed operation and a known denied operation for the backend and configuration rehearsed for the demo. Show the actual decision evidence.
4. **60 seconds — change central policy.** Publish a new artifact, confirm the sync and effective policy version, then repeat the operation. Rehearse refresh timing on the exact nightly.
5. **60 seconds — separate tool controls.** If the optional tier is implemented, show a permitted MCP tool and a denied tool. Explain that downstream AWS permissions still apply even after gateway authorization.
6. **40 seconds — close with evidence.** Compare CloudTrail SSM API activity with Crew/MCP application events. Do not imply the tunnel records tool payloads.

Rehearse real policy refresh, authentication and MCP deployment before presenting them as implemented. The architecture requires no public Gateway endpoint; a public ALB or API Gateway would add a separate application authentication and exposure design.

## Source basis

- [SSM port-forwarding requirements and parameters](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html#sessions-start-port-forwarding)
- [Systems Manager VPC endpoints](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html)
- [SSM message API and Region differences](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-setting-up-messageAPIs.html)
- [Scope human Session Manager permissions](https://docs.aws.amazon.com/systems-manager/latest/userguide/getting-started-restrict-access-examples.html)
- [SSM instance profile](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started-instance-profile.html)
- [Session Manager audit coverage and port-forwarding limitations](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-auditing.html)
- [S3 gateway endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html)
- [CloudWatch Agent log collection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html)
- [ECS task IAM roles](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)
- [Network Firewall routing](https://docs.aws.amazon.com/network-firewall/latest/developerguide/route-tables.html)
- [Pinned KiroCrew nightly CLI manifest](https://download.crew.kiro.dev/cli/nightly/0.7.0.dev20260911060948/cli-manifest.json). Policy behavior was checked in `kiro_crew/platform/policy_distribution.py` inside that nightly wheel.
- [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/) and [AWS Labs icon source](https://github.com/awslabs/aws-icons-for-plantuml/tree/e26e2c05daf8b6bc4c764669fc2be04c314ccb8c). Ten PNG service icons are embedded locally; the HTML does not fetch icons at runtime.

## Artifact evidence

The source JSON and base HTML passed Archify's nine showcase artifact checks with no composition errors or warnings. AWS icons were added to a separate derivative, which passed the same nine artifact checks. The source and base HTML were preserved; icon hashes are recorded in `kirocrew-aws-icons.json`.

The static PNG was visually inspected. Full HTML browser checks could not run because local Chrome/Chromium was unavailable; responsive containment, viewer interactions and in-browser exports remain unverified. The static preview uses a font fallback and adds a title and concise notes.

The companion source archive includes the checked base, final HTML, JSON, icon assets and provenance, postprocessor, notes and receipt. It complements the earlier logical KiroCrew diagram.


## Endpoint visual revision receipt

One endpoint panel now contains enterprise host protection, the Crew runtime, policy enforcement, L0–L5 and cross-cutting controls. The subagent review found no blocking issues; the minor legend finding was corrected and re-reviewed in both themes.

```text
diagram_type: architecture
output: kirocrew-security-layers.html
specification_sha256: fa3662e9483a6dbac6fa505fa3b5e855e42134246d5d08e3122013bd7d4f4d55
base_artifact_sha256: f51ac796f42f996f84cf7050cb440eb11ffef19a1f9c4c45e66fa8efd581e882
detailed_artifact_sha256: 602c595aa2caa1a89ea1387e50c2a11a4c576e922ce027e95c43c05ac9362fe9
validation: 9/9 showcase, 0 errors, 0 warnings
browser_evidence: skipped (Chromium unavailable)
visual_review: passed (static light/dark previews)
correction_rounds: 1
```
