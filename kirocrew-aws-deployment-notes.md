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
