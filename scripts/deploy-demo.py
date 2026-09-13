#!/usr/bin/env python3
"""Plan, create, and explicitly execute a portable-demo CloudFormation change set."""
import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'infrastructure' / 'portable-demo.json'
CANONICAL_OWNER = '099720109477'
LIMITS = [
    'Route configuration is not an end-to-end connectivity test. NACL rules, upstream routes, appliances, DNS answers, destination security groups and endpoint policies still need review.',
    'The new security group admits only TCP 22 from AllowedCidr. That must be the source address the instance sees, including any VPN/bastion translation.',
    'Bootstrap needs reachable Ubuntu apt/snap repositories and AWS SSM APIs. Egress CIDRs do not configure proxies, mirrors or VPC endpoints.',
    'CREATE_COMPLETE does not establish bootstrap success or a signed-in native Kiro CLI backend.',
]


class ValidationError(Exception):
    pass


class AwsError(ValidationError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def load_parameters(path, template):
    data = json.loads(Path(path).read_text())
    if not isinstance(data, list):
        raise ValidationError('Parameters must be a CloudFormation JSON list of ParameterKey/ParameterValue objects.')
    supplied = {}
    for item in data:
        if not isinstance(item, dict) or set(item) != {'ParameterKey', 'ParameterValue'}:
            raise ValidationError('Each parameter must contain exactly ParameterKey and ParameterValue; UsePreviousValue is not supported.')
        key, value = item['ParameterKey'], item['ParameterValue']
        if not isinstance(key, str) or not isinstance(value, str) or key in supplied:
            raise ValidationError('Parameter keys must be unique strings and values must be strings.')
        if key not in template['Parameters']:
            raise ValidationError(f'Unknown parameter: {key}')
        supplied[key] = value
    values = {}
    for key, spec in template['Parameters'].items():
        if key not in supplied and 'Default' not in spec:
            raise ValidationError(f'Missing explicit parameter: {key}')
        value = supplied.get(key, str(spec.get('Default')))
        if not value:
            raise ValidationError(f'{key} cannot be empty.')
        if 'AllowedValues' in spec and value not in spec['AllowedValues']:
            raise ValidationError(f'{key} must be one of {spec["AllowedValues"]}.')
        if 'AllowedPattern' in spec and re.fullmatch(spec['AllowedPattern'], value) is None:
            raise ValidationError(f'{key} does not match its allowed format.')
        if spec['Type'] == 'Number':
            try:
                number = int(value)
            except ValueError as exc:
                raise ValidationError(f'{key} must be a whole number.') from exc
            if not spec.get('MinValue', number) <= number <= spec.get('MaxValue', number):
                raise ValidationError(f'{key} is outside its allowed range.')
        values[key] = value
    for key in ('AllowedCidr', 'HttpsEgressCidr', 'HttpEgressCidr'):
        try:
            network = ipaddress.IPv4Network(values[key], strict=True)
        except ValueError as exc:
            raise ValidationError(f'{key} must be a canonical IPv4 CIDR.') from exc
        if key == 'AllowedCidr' and network.prefixlen != 32:
            raise ValidationError('AllowedCidr must name exactly one IPv4 /32.')
    for key, prefix in (('VpcId', 'vpc'), ('SubnetId', 'subnet'), ('ImageId', 'ami')):
        if not re.fullmatch(prefix + r'-[0-9a-f]{8}(?:[0-9a-f]{9})?', values[key]):
            raise ValidationError(f'{key} must be an explicit {prefix} ID.')
    return values


def parameter_list(values):
    return [{'ParameterKey': key, 'ParameterValue': value} for key, value in sorted(values.items())]


class Aws:
    def __init__(self, region, profile=None):
        self.prefix = ['aws', '--region', region, '--output', 'json', '--no-cli-pager']
        if profile:
            self.prefix += ['--profile', profile]

    def __call__(self, service, operation, *args):
        env = dict(os.environ, AWS_PAGER='', AWS_CLI_AUTO_PROMPT='off')
        try:
            result = subprocess.run(self.prefix + [service, operation, *args], capture_output=True, text=True, env=env, timeout=180, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AwsError(f'AWS CLI unavailable or timed out for {service} {operation}.') from exc
        if result.returncode:
            raise AwsError(f'{service} {operation}: {result.stderr.strip()}')
        return json.loads(result.stdout) if result.stdout.strip() else {}


def only(items, what):
    if len(items) != 1:
        raise ValidationError(f'Expected exactly one {what}; found {len(items)}.')
    return items[0]


def effective_table(tables, subnet_id):
    explicit = [table for table in tables if any(a.get('SubnetId') == subnet_id for a in table.get('Associations', []))]
    if explicit:
        return only(explicit, 'explicit subnet route table')
    return only([table for table in tables if any(a.get('Main') is True for a in table.get('Associations', []))], 'main VPC route table')


def route_target(route):
    for key in ('NatGatewayId', 'TransitGatewayId', 'VpcPeeringConnectionId', 'NetworkInterfaceId', 'InstanceId', 'VpcEndpointId', 'GatewayId', 'LocalGatewayId', 'CarrierGatewayId', 'CoreNetworkArn'):
        if route.get(key):
            return {key: route[key]}
    return {}


def route_segments(routes, destination):
    """Longest-prefix routes across the requested CIDR, including missing/blackhole ranges."""
    requested = ipaddress.IPv4Network(destination)
    start, stop = int(requested.network_address), int(requested.broadcast_address) + 1
    candidates, cuts = [], {start, stop}
    for route in routes:
        if 'DestinationCidrBlock' not in route:
            continue
        network = ipaddress.IPv4Network(route['DestinationCidrBlock'])
        low, high = max(start, int(network.network_address)), min(stop, int(network.broadcast_address) + 1)
        if low < high:
            candidates.append((network, route))
            cuts.update((low, high))
    result = []
    ordered = sorted(cuts)
    for low, high in zip(ordered, ordered[1:]):
        address = ipaddress.IPv4Address(low)
        matches = [(network.prefixlen, route) for network, route in candidates if address in network]
        route = max(matches, key=lambda item: item[0])[1] if matches else None
        result.append({'from': str(address), 'through': str(ipaddress.IPv4Address(high - 1)), 'route': route})
    return result


def existing_stack(aws, stack_name):
    try:
        return only(aws('cloudformation', 'describe-stacks', '--stack-name', stack_name).get('Stacks', []), 'stack')
    except AwsError as exc:
        if 'ValidationError' in str(exc) and 'does not exist' in str(exc):
            return None
        raise


def check_template(template):
    raw = (ROOT / 'infrastructure' / 'bootstrap.sh').read_text()
    if template['Resources']['DemoInstance']['Properties']['UserData'] != {'Fn::Base64': raw}:
        raise ValidationError('Portable UserData differs from infrastructure/bootstrap.sh; review and synchronize before deploying.')
    if [r['Type'] for r in template['Resources'].values()].count('AWS::EC2::Instance') != 1:
        raise ValidationError('Portable template must contain exactly one EC2 instance.')


def preflight(aws, values, template, stack_name):
    caller = aws('sts', 'get-caller-identity')
    if not caller.get('Arn', '').startswith('arn:aws:'):
        raise ValidationError('This Canonical owner check currently supports the commercial AWS partition only.')
    stack = existing_stack(aws, stack_name)
    if stack and stack['StackStatus'] != 'REVIEW_IN_PROGRESS':
        deployed = aws('cloudformation', 'get-template', '--stack-name', stack_name).get('TemplateBody')
        deployed = json.loads(deployed) if isinstance(deployed, str) else deployed
        if 'DemoArmInstance' in deployed.get('Resources', {}) or 'LegacyInstanceId' in deployed.get('Outputs', {}):
            raise ValidationError('This is the historical two-host stack. Use a new stack name; migrating that stack is outside this module.')
        if deployed.get('Metadata', {}).get('PortableDemoVersion') != 1:
            raise ValidationError('Existing stack is not a portable-demo stack. Choose a new stack name.')
        if stack['StackStatus'] not in ('CREATE_COMPLETE', 'UPDATE_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE', 'REVIEW_IN_PROGRESS'):
            raise ValidationError(f'Stack status is not ready for a change set: {stack["StackStatus"]}.')
    if (not stack or stack['StackStatus'] == 'REVIEW_IN_PROGRESS') and values['AllowHttpEgress'] != 'true':
        raise ValidationError('Initial stock Ubuntu bootstrap requires HTTP apt access. Set AllowHttpEgress=true; disable it only in a reviewed post-bootstrap update.')
    vpc = only(aws('ec2', 'describe-vpcs', '--vpc-ids', values['VpcId']).get('Vpcs', []), 'VPC')
    subnet = only(aws('ec2', 'describe-subnets', '--subnet-ids', values['SubnetId']).get('Subnets', []), 'subnet')
    if vpc.get('State') != 'available' or subnet.get('State') != 'available':
        raise ValidationError('The supplied VPC and subnet must both be available.')
    if subnet.get('VpcId') != values['VpcId'] or subnet.get('Ipv6Native'):
        raise ValidationError('Subnet must belong to VpcId and support IPv4.')
    if subnet.get('AvailableIpAddressCount', 0) < 1:
        raise ValidationError('Subnet has no available IPv4 addresses.')
    dns = aws('ec2', 'describe-vpc-attribute', '--vpc-id', values['VpcId'], '--attribute', 'enableDnsSupport')
    if not dns.get('EnableDnsSupport', {}).get('Value'):
        raise ValidationError('VPC enableDnsSupport must already be true; this tool will not change it.')
    dhcp = only(aws('ec2', 'describe-dhcp-options', '--dhcp-options-ids', vpc['DhcpOptionsId']).get('DhcpOptions', []), 'DHCP options set')
    servers = [item['Value'] for c in dhcp.get('DhcpConfigurations', []) if c.get('Key') == 'domain-name-servers' for item in c.get('Values', [])]
    if servers != ['AmazonProvidedDNS']:
        raise ValidationError('This bootstrap/egress contract requires existing AmazonProvidedDNS DHCP configuration. Custom DNS needs a separately reviewed adaptation.')
    image = only(aws('ec2', 'describe-images', '--image-ids', values['ImageId']).get('Images', []), 'AMI')
    architecture = image.get('Architecture')
    expected_arch = {'arm64': 'arm64', 'x86_64': 'amd64'}.get(architecture)
    expected_name = rf'ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24\.04-{expected_arch}-server-\d{{8}}(?:\.\d+)?'
    if (image.get('OwnerId') != CANONICAL_OWNER or image.get('State') != 'available'
        or image.get('RootDeviceType') != 'ebs' or image.get('VirtualizationType') != 'hvm'
        or image.get('RootDeviceName') != '/dev/sda1' or not expected_arch
        or not re.fullmatch(expected_name, image.get('Name', ''))):
        raise ValidationError('ImageId must be an available Canonical Ubuntu Server 24.04 standard EBS/HVM AMI with /dev/sda1 root in this region.')
    instance = only(aws('ec2', 'describe-instance-types', '--instance-types', values['InstanceType']).get('InstanceTypes', []), 'instance type')
    if architecture not in instance.get('ProcessorInfo', {}).get('SupportedArchitectures', []):
        raise ValidationError('AMI architecture does not match InstanceType.')
    if instance.get('VCpuInfo', {}).get('DefaultVCpus', 0) < 4 or instance.get('MemoryInfo', {}).get('SizeInMiB', 0) < 16384:
        raise ValidationError('InstanceType is below the accepted 4 vCPU / 16 GiB baseline.')
    offerings = aws('ec2', 'describe-instance-type-offerings', '--location-type', 'availability-zone', '--filters', f'Name=location,Values={subnet["AvailabilityZone"]}', f'Name=instance-type,Values={values["InstanceType"]}').get('InstanceTypeOfferings', [])
    if not offerings:
        raise ValidationError('Instance type is not offered in the supplied subnet availability zone.')
    only(aws('ec2', 'describe-key-pairs', '--key-names', values['KeyName']).get('KeyPairs', []), 'existing key pair')
    tables = aws('ec2', 'describe-route-tables', '--filters', f'Name=vpc-id,Values={values["VpcId"]}').get('RouteTables', [])
    table = effective_table(tables, values['SubnetId'])
    checks, warnings = {}, []
    destinations = {'administratorReturnPath': values['AllowedCidr'], 'httpsDestinations': values['HttpsEgressCidr']}
    if values['AllowHttpEgress'] == 'true':
        destinations['httpDestinations'] = values['HttpEgressCidr']
    for name, destination in destinations.items():
        segments = route_segments(table.get('Routes', []), destination)
        checks[name] = segments
        for segment in segments:
            route = segment['route']
            if not route or route.get('State') != 'active':
                warnings.append(f'{name}: route coverage is missing or inactive for {segment["from"]} through {segment["through"]}.')
            elif name == 'administratorReturnPath' and route.get('NatGatewayId'):
                warnings.append('administratorReturnPath: NAT does not establish incoming SSH; verify an existing VPN/bastion/SSM administration path.')
            elif route.get('GatewayId', '').startswith('igw-') and values['AssociatePublicIpAddress'] == 'false':
                warnings.append(f'{name}: a direct IGW route cannot provide IPv4 connectivity without a public address; existing private paths must cover the required destinations.')
    targets = {json.dumps(route_target(s['route']), sort_keys=True) for segments in checks.values() for s in segments if s['route'] and s['route'].get('State') == 'active'}
    target_checks = []
    for encoded in sorted(targets):
        target = json.loads(encoded)
        if target.get('GatewayId', '').startswith('igw-'):
            gateway = only(aws('ec2', 'describe-internet-gateways', '--internet-gateway-ids', target['GatewayId']).get('InternetGateways', []), 'internet gateway')
            if not any(a.get('VpcId') == values['VpcId'] and a.get('State') == 'available' for a in gateway.get('Attachments', [])):
                raise ValidationError('An effective IGW route does not target an attached available internet gateway.')
            target_checks.append(dict(target, attachment='verified'))
        elif target.get('NatGatewayId'):
            nat = only(aws('ec2', 'describe-nat-gateways', '--nat-gateway-ids', target['NatGatewayId']).get('NatGateways', []), 'NAT gateway')
            if nat.get('State') != 'available':
                raise ValidationError('An effective NAT gateway route targets an unavailable NAT gateway.')
            target_checks.append(dict(target, state='available', upstreamPath='not verified'))
        else:
            target_checks.append(dict(target, upstreamPath='not verified'))
    acl = aws('ec2', 'describe-network-acls', '--filters', f'Name=association.subnet-id,Values={values["SubnetId"]}').get('NetworkAcls', [])
    if len(acl) != 1:
        raise ValidationError('Expected one associated subnet network ACL.')
    warnings = list(dict.fromkeys(warnings))
    if any(values[k] != '0.0.0.0/0' for k in ('HttpsEgressCidr', 'HttpEgressCidr')):
        warnings.append('Egress destinations are restricted. Verify that all stock Ubuntu/snap/AWS/backend destinations are within the allowed CIDRs; the bootstrap does not configure a mirror or proxy.')
    return {
        'caller': {'account': caller['Account'], 'arn': caller['Arn']},
        'stackName': stack_name, 'changeSetType': 'CREATE' if not stack or stack['StackStatus'] == 'REVIEW_IN_PROGRESS' else 'UPDATE',
        'templateSha256': digest(template), 'parameters': parameter_list(values),
        'network': {'vpcId': vpc['VpcId'], 'subnetId': subnet['SubnetId'], 'availabilityZone': subnet['AvailabilityZone'], 'publicIpAssignment': values['AssociatePublicIpAddress'], 'routeTableId': table['RouteTableId'], 'routes': table.get('Routes', []), 'effectiveDestinationRoutes': checks, 'targetChecks': target_checks, 'networkAcl': {'id': acl[0]['NetworkAclId'], 'entries': acl[0].get('Entries', [])}},
        'image': {k: image.get(k) for k in ('ImageId', 'Name', 'OwnerId', 'Architecture', 'CreationDate')},
        'instanceType': values['InstanceType'], 'warnings': warnings, 'limits': LIMITS,
    }


def checked_change_set(aws, arn, stack_name, values, template, allow_replacement):
    if not re.fullmatch(r'arn:aws:cloudformation:[a-z0-9-]+:\d{12}:changeSet/[^/]+/[^/]+', arn):
        raise ValidationError('Execution requires the full change-set ARN returned by the create step.')
    change = aws('cloudformation', 'describe-change-set', '--change-set-name', arn, '--stack-name', stack_name)
    if change.get('StackName') != stack_name or change.get('Status') != 'CREATE_COMPLETE' or change.get('ExecutionStatus') != 'AVAILABLE':
        raise ValidationError('Named change set is not available for this stack.')
    actual = {p['ParameterKey']: p.get('ParameterValue') for p in change.get('Parameters', [])}
    if actual != values:
        raise ValidationError('Change-set parameters differ from the reviewed parameter file.')
    saved = aws('cloudformation', 'get-template', '--stack-name', stack_name, '--change-set-name', arn, '--template-stage', 'Original').get('TemplateBody')
    saved = json.loads(saved) if isinstance(saved, str) else saved
    if digest(saved) != digest(template):
        raise ValidationError('Change-set template differs from the local portable template; re-plan the actual candidate.')
    fresh_host = any(c.get('ResourceChange', {}).get('LogicalResourceId') == 'DemoInstance' and (c['ResourceChange'].get('Action') == 'Add' or c['ResourceChange'].get('Replacement') in ('True', 'Conditional')) for c in change.get('Changes', []))
    if fresh_host and values['AllowHttpEgress'] != 'true':
        raise ValidationError('Adding or replacing DemoInstance requires HTTP apt access for fresh bootstrap; AllowHttpEgress must be true.')
    destructive = [c['ResourceChange'] for c in change.get('Changes', []) if c.get('ResourceChange', {}).get('Action') == 'Remove' or c.get('ResourceChange', {}).get('Replacement') in ('True', 'Conditional')]
    if destructive and not allow_replacement:
        raise ValidationError('Change set may remove or replace resources. Review it and explicitly add --allow-replacement only if intended: ' + json.dumps(destructive))
    return change


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('plan', 'create-change-set', 'execute'), nargs='?', default='plan')
    p.add_argument('--parameters', type=Path, required=True, help='Native CloudFormation ParameterKey/ParameterValue JSON list.')
    p.add_argument('--stack-name', required=True)
    p.add_argument('--region', default='us-east-1')
    p.add_argument('--profile')
    p.add_argument('--apply', action='store_true', help='Permit the selected CloudFormation mutation; plan is always read-only.')
    p.add_argument('--change-set', help='Full ARN required for execute.')
    p.add_argument('--allow-replacement', action='store_true', help='Explicitly permit reviewed removal/conditional replacement on execute.')
    p.add_argument('--acknowledge-network-review', action='store_true', help='Acknowledge unresolved route coverage or restricted destination warnings after network review.')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]{0,127}', args.stack_name):
            raise ValidationError('Stack name must begin with a letter and contain at most 128 letters, digits or hyphens.')
        if args.command != 'plan' and not args.apply:
            raise ValidationError('CloudFormation mutation requires --apply. Start with the read-only plan command.')
        if args.command == 'plan' and args.apply:
            raise ValidationError('plan is read-only; select create-change-set or execute explicitly.')
        template = json.loads(TEMPLATE.read_text())
        check_template(template)
        values = load_parameters(args.parameters, template)
        aws = Aws(args.region, args.profile)
        report = preflight(aws, values, template, args.stack_name)
        report['region'] = args.region
        report['operation'] = args.command
        if args.command == 'plan':
            print(json.dumps(report, indent=2))
            return 0
        if report['warnings'] and not args.acknowledge_network_review:
            print(json.dumps(report, indent=2))
            raise ValidationError('Review network warnings before mutation. If existing connectivity is verified, repeat with --acknowledge-network-review; no network resource will be modified.')
        if args.command == 'create-change-set':
            name = 'portable-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
            with tempfile.TemporaryDirectory(prefix='kirocrew-cfn-') as temp:
                params_path = Path(temp) / 'parameters.json'
                template_path = Path(temp) / 'template.json'
                params_path.write_text(json.dumps(parameter_list(values)))
                template_path.write_text(json.dumps(template))
                created = aws('cloudformation', 'create-change-set', '--stack-name', args.stack_name, '--change-set-name', name, '--change-set-type', report['changeSetType'], '--template-body', 'file://' + str(template_path), '--parameters', 'file://' + str(params_path), '--capabilities', 'CAPABILITY_IAM', '--description', 'Reviewed portable KiroCrew candidate; template sha256 ' + digest(template))
            report['changeSet'] = created
            report['nextStep'] = 'Wait for CREATE_COMPLETE, inspect describe-change-set, then execute this exact ARN with the same parameters. No resources are deployed by this command.'
        else:
            if not args.change_set:
                raise ValidationError('execute requires --change-set with the full reviewed ARN.')
            change = checked_change_set(aws, args.change_set, args.stack_name, values, template, args.allow_replacement)
            report['reviewedChanges'] = change.get('Changes', [])
            aws('cloudformation', 'execute-change-set', '--change-set-name', args.change_set, '--stack-name', args.stack_name, '--client-request-token', 'portable-' + uuid.uuid4().hex)
            report['executionStarted'] = True
            report['nextStep'] = 'Inspect stack events and outputs. Verify /opt/kirocrew-demo/bootstrap-complete separately before runtime installation.'
        print(json.dumps(report, indent=2))
        return 0
    except (ValidationError, ValueError, OSError, KeyError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
