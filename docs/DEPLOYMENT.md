# Deploy into an existing network

`infrastructure/portable-demo.json` creates one EC2 instance in the VPC and subnet you supply. Its default is `t4g.xlarge` (ARM, 4 vCPU / 16 GiB), with a 40 GiB encrypted gp3 root volume. It retains the demo's scoped instance role, private S3 bucket, single-source SSH rule and crew UID metadata guard. It creates no VPC, subnet, NAT gateway, internet gateway, route, VPC endpoint or load balancer.

The existing `infrastructure/ec2-demo.json` describes the historical two-host deployment. Keep it as a record. The helper refuses to apply the portable template to that stack or an unrelated existing stack. Use a new stack name for this edition; its later updates use reviewed change sets.

## Prepare parameters

Use Python 3.12 or newer and AWS CLI v2 on macOS, Linux or Windows. Authenticate the AWS CLI on that machine using your normal profile or environment. Credentials and SSH private keys stay outside this repository. All commands below run from the repository root; the helper resolves its template relative to its own file, so it also works from other directories when given absolute paths.

Copy one example to your local configuration, then replace the example IDs and addresses:

```sh
cp config/cloudformation-public.example.json config/cloudformation.local.json
```

For an existing private subnet, copy `config/cloudformation-private.example.json` instead. Both files use CloudFormation's native list of `ParameterKey` / `ParameterValue` objects. Every value is a string. The helper rejects unknown or duplicate parameters and `UsePreviousValue`; each candidate contains the full reviewed configuration.

| Parameter | What to supply |
| --- | --- |
| `VpcId` | An existing VPC in the chosen region. No default VPC is looked up. |
| `SubnetId` | One existing IPv4 subnet in that VPC. Nothing changes its routing. |
| `ImageId` | A region-specific Canonical Ubuntu Server 24.04 standard EBS/HVM AMI matching the instance architecture. |
| `KeyName` | An existing EC2 key pair in that region; this is its name, never its private key. |
| `AllowedCidr` | Exactly one administrator source IPv4 `/32`, as the instance sees it. Use the public address for direct internet SSH, or the existing VPN/bastion source address for private access. |
| `AssociatePublicIpAddress` | Explicit `true` or `false`. This overrides subnet public-IP auto-assignment. |
| `InstanceType` | Defaults to `t4g.xlarge`. Supported alternatives are `t4g.2xlarge`, `t3a.xlarge` and `t3a.2xlarge`, each with a matching AMI. |
| `HttpsEgressCidr` | IPv4 destinations allowed on TCP 443. Required, with no hidden default. |
| `HttpEgressCidr` | IPv4 destinations allowed on TCP 80 while HTTP egress is enabled. Required, with no hidden default. |
| `AllowHttpEgress` | `true` for stock Ubuntu bootstrap. A later reviewed update may set `false` after package access and maintenance requirements are addressed. |
| `RootVolumeGiB` | Defaults to `40`; supports 40–200 GiB. The volume is deleted with the instance. |

The example egress CIDRs are `0.0.0.0/0` on ports 80 and 443 so the unmodified Ubuntu/snap bootstrap can reach its repositories. Narrow them only when the destinations are known and the existing network already supports them. These parameters do not configure a proxy or mirror. The included bootstrap has no proxy/mirror parameters, and AWS service endpoints alone do not provide Ubuntu repositories. [SSM VPC connectivity requirements](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html)

Find the current ARM AMI without deploying anything, then copy the returned AMI ID into your parameter file. Use the same region/profile as the deployment:

```sh
aws ssm get-parameter --region us-east-1 --profile YOUR-PROFILE \
  --name /aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id \
  --query Parameter.Value --output text
```

For the `t3a` alternatives, use `amd64` in that parameter path. The helper checks the explicit AMI's owner, available state, Ubuntu 24.04 image name, EBS/HVM root and architecture against EC2's instance-type data; it also checks that the type is offered in the subnet's availability zone. It currently supports the commercial AWS partition and Canonical owner `099720109477`. It does not silently replace the AMI with a newer image. [Canonical image discovery and ownership](https://ubuntu.com/aws/docs/aws-how-to/instances/find-ubuntu-images/)

## Inspect, create a change set, then execute it

Start with the read-only plan. `--region` defaults to `us-east-1`; `--profile` is optional if your normal AWS credential chain is already configured.

```sh
python3 scripts/deploy-demo.py plan \
  --parameters config/cloudformation.local.json \
  --stack-name YOUR-NEW-STACK --region us-east-1 --profile YOUR-PROFILE
```

The JSON report identifies the caller account, selected resources, full parameters, template digest, routes, associated NACL entries and validation limits. Inspect it before creating anything. Check that the caller account and region are the ones you intend to use.

Create a reviewable change set:

```sh
python3 scripts/deploy-demo.py create-change-set --apply \
  --parameters config/cloudformation.local.json \
  --stack-name YOUR-NEW-STACK --region us-east-1 --profile YOUR-PROFILE
```

This registers a CloudFormation candidate; it does not execute it. For a new stack, CloudFormation creates an empty `REVIEW_IN_PROGRESS` stack while preparing the candidate. Use the returned full change-set ARN, wait for it to become ready, and inspect its resource changes. [CloudFormation CreateChangeSet behavior](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_CreateChangeSet.html)

```sh
aws cloudformation wait change-set-create-complete \
  --stack-name YOUR-NEW-STACK --change-set-name FULL_CHANGE_SET_ARN \
  --region us-east-1 --profile YOUR-PROFILE

aws cloudformation describe-change-set \
  --stack-name YOUR-NEW-STACK --change-set-name FULL_CHANGE_SET_ARN \
  --region us-east-1 --profile YOUR-PROFILE
```

Execute that specific candidate with the same parameter file:

```sh
python3 scripts/deploy-demo.py execute --apply \
  --change-set FULL_CHANGE_SET_ARN \
  --parameters config/cloudformation.local.json \
  --stack-name YOUR-NEW-STACK --region us-east-1 --profile YOUR-PROFILE
```

The helper rechecks the environment and compares the stored candidate's template and parameters with your local files before execution. If a change can remove or replace a resource, it stops until you explicitly pass `--allow-replacement` after reviewing those changes. Changing the subnet, public-IP assignment or AMI can replace the host. Any added or replaced host must have HTTP bootstrap egress enabled, even when replacement is acknowledged. [EC2 network-interface replacement properties](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-ec2-instance-networkinterface.html)

The commands return after starting their operation. Inspect CloudFormation stack events and outputs for its final result. A failed or empty change set is never executed automatically. Remove an unwanted change set explicitly in your normal CloudFormation workflow; this helper has no deletion command.

## Existing-network checks and limits

The helper verifies VPC/subnet availability and membership, IPv4 capacity, VPC DNS support and existing `AmazonProvidedDNS` DHCP configuration. A CloudFormation rule also checks subnet-to-VPC membership when the template is used directly. The current bootstrap and security-group contract require AmazonProvidedDNS; custom DNS needs a separately reviewed adaptation. [CloudFormation rule functions](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/intrinsic-function-reference-rules.html)

It selects the subnet's explicitly associated route table, or the VPC's main route table when that association is implicit. It applies longest-prefix matching across the administrator `/32` and configured egress CIDRs, so a narrower blackhole route is visible even when a default route exists. Specific routes are supported; a default route is not required. [AWS subnet route tables](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)

For effective IGW routes it checks the gateway's VPC attachment; for NAT gateway routes it checks that the NAT gateway is available. Existing transit gateway, VPN, peering and appliance paths remain possible. Their upstream route tables, return routes and firewalls are outside this local preflight. A direct IGW route cannot provide internet IPv4 connectivity for a host without a public address. A NAT gateway route does not establish incoming SSH. [Internet gateway routing](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html), [NAT behavior](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat.html)

Missing/inactive route coverage, NAT-only administration, private-host IGW routing, or restricted destination CIDRs produce concrete warnings. Read-only planning still prints them. Creating or executing a candidate with those warnings requires `--acknowledge-network-review` after verifying the existing network path. That flag changes no network resource and does not turn the warnings into proof of reachability.

Even a plan with no warnings does not prove end-to-end access. Review the displayed subnet NACL, including return traffic; existing destination security groups, endpoint policies, DNS answers and upstream appliances can still block traffic. The instance security group exposes only TCP 22 from the configured `/32`. Gateway, MCP and telemetry ports stay on loopback when installed by the runtime module. Use your existing SSH forwarding, VPN/bastion path or SSM connectivity to reach them.

## Finish the host and runtime setup

The stack outputs preserve the runtime contract: `InstanceId`, `SecurityGroupId`, `DemoBucketName`, `InstanceRoleName` and `InstanceRoleArn`. `PrivateIp`, `VpcId` and `SubnetId` are always available; `PublicIp` is emitted only when public-IP assignment is enabled. A public IP may change after stop/start.

The bootstrap bytes exactly match `infrastructure/bootstrap.sh`; its historical amd64 comment is preserved, while the package commands support both selected architectures. It creates service users, installs base packages and SSM, requires IMDSv2, and blocks the crew UID from both metadata addresses. The MCP UID and host administrators retain instance-role access. It does not install a Crew release or authenticate Kiro CLI.

Before runtime installation, use your chosen administration path to verify:

```sh
sudo test -f /opt/kirocrew-demo/bootstrap-complete
sudo systemctl is-active kirocrew-imds-guard.service
```

CloudFormation does not wait for a bootstrap signal. Inspect `/var/log/cloud-init-output.log` if the marker is absent. Continue with the modular runtime setup in the repository README after the host checks pass. A successful stack and direct MCP probe remain separate from native Kiro CLI sign-in and enforcement acceptance.

The S3 bucket and its TLS-only bucket policy are retained on stack deletion. Review and explicitly empty/delete retained resources when the demo is retired. No cleanup or deletion is performed by this helper. GitHub Actions are outside this workflow.
