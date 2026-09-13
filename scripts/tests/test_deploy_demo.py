"""Portable deployment contract tests; AWS calls use fixtures only."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('deploy_demo', ROOT / 'scripts/deploy-demo.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
TEMPLATE = json.loads(m.TEMPLATE.read_text())
PARAMETERS = json.loads((ROOT / 'config/cloudformation-public.example.json').read_text())
VALUES = {p['ParameterKey']: p['ParameterValue'] for p in PARAMETERS}
ARN = 'arn:aws:cloudformation:us-east-1:123456789012:changeSet/portable-test/11111111-2222-3333-4444-555555555555'
LOCAL = {'DestinationCidrBlock': '10.0.0.0/16', 'GatewayId': 'local', 'State': 'active'}
INTERNET = {'DestinationCidrBlock': '0.0.0.0/0', 'GatewayId': 'igw-example', 'State': 'active'}


class FixtureAws:
    def __init__(self):
        self.calls = []
        self.stack = None
        self.template = copy.deepcopy(TEMPLATE)
        self.routes = [copy.deepcopy(LOCAL), copy.deepcopy(INTERNET)]
        self.subnet = {'SubnetId': VALUES['SubnetId'], 'VpcId': VALUES['VpcId'], 'State': 'available', 'AvailableIpAddressCount': 25, 'AvailabilityZone': 'us-east-1a'}
        self.image = {'ImageId': VALUES['ImageId'], 'Architecture': 'arm64', 'Name': 'ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-20260901', 'OwnerId': m.CANONICAL_OWNER, 'State': 'available', 'RootDeviceType': 'ebs', 'VirtualizationType': 'hvm', 'RootDeviceName': '/dev/sda1'}
        self.architectures = ['arm64']
        self.change = {'StackName': 'test-demo', 'Status': 'CREATE_COMPLETE', 'ExecutionStatus': 'AVAILABLE', 'Parameters': copy.deepcopy(PARAMETERS), 'Changes': [{'ResourceChange': {'Action': 'Add', 'LogicalResourceId': 'DemoInstance'}}]}
        self.dns = True

    def __call__(self, service, operation, *args):
        self.calls.append((service, operation, args))
        if operation == 'get-caller-identity':
            return {'Account': '123456789012', 'Arn': 'arn:aws:iam::123456789012:user/fixture'}
        if operation == 'describe-stacks':
            if self.stack is None:
                raise m.AwsError('ValidationError: Stack with id test-demo does not exist')
            return {'Stacks': [self.stack]}
        if operation == 'get-template':
            return {'TemplateBody': self.template}
        if operation == 'describe-vpcs':
            return {'Vpcs': [{'VpcId': VALUES['VpcId'], 'State': 'available', 'DhcpOptionsId': 'dopt-example'}]}
        if operation == 'describe-subnets':
            return {'Subnets': [self.subnet]}
        if operation == 'describe-vpc-attribute':
            return {'EnableDnsSupport': {'Value': self.dns}}
        if operation == 'describe-dhcp-options':
            return {'DhcpOptions': [{'DhcpConfigurations': [{'Key': 'domain-name-servers', 'Values': [{'Value': 'AmazonProvidedDNS'}]}]}]}
        if operation == 'describe-images':
            return {'Images': [self.image]}
        if operation == 'describe-instance-types':
            return {'InstanceTypes': [{'ProcessorInfo': {'SupportedArchitectures': self.architectures}, 'VCpuInfo': {'DefaultVCpus': 4}, 'MemoryInfo': {'SizeInMiB': 16384}}]}
        if operation == 'describe-instance-type-offerings':
            return {'InstanceTypeOfferings': [{'InstanceType': VALUES['InstanceType']}]}
        if operation == 'describe-key-pairs':
            return {'KeyPairs': [{'KeyName': VALUES['KeyName']}]}
        if operation == 'describe-route-tables':
            return {'RouteTables': [{'RouteTableId': 'rtb-example', 'Associations': [{'Main': True}], 'Routes': self.routes}]}
        if operation == 'describe-internet-gateways':
            return {'InternetGateways': [{'Attachments': [{'VpcId': VALUES['VpcId'], 'State': 'available'}]}]}
        if operation == 'describe-nat-gateways':
            return {'NatGateways': [{'State': 'available'}]}
        if operation == 'describe-network-acls':
            return {'NetworkAcls': [{'NetworkAclId': 'acl-example', 'Entries': []}]}
        if operation == 'describe-change-set':
            return self.change
        if operation == 'create-change-set':
            return {'Id': ARN, 'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/test-demo/example'}
        if operation == 'execute-change-set':
            return {}
        raise AssertionError(f'Unexpected AWS call {service} {operation}')


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.aws = FixtureAws()
        self.values = dict(VALUES)

    def params(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'params.json'
            path.write_text(json.dumps(data))
            return m.load_parameters(path, TEMPLATE)

    def preflight(self):
        return m.preflight(self.aws, self.values, TEMPLATE, 'test-demo')

    def test_explicit_network_required_and_strict_parameter_list(self):
        self.assertEqual(self.params(PARAMETERS), VALUES)
        for excluded in ('VpcId', 'SubnetId', 'AssociatePublicIpAddress', 'AllowedCidr'):
            with self.subTest(excluded=excluded), self.assertRaises(m.ValidationError):
                self.params([p for p in PARAMETERS if p['ParameterKey'] != excluded])
        with self.assertRaises(m.ValidationError):
            self.params(PARAMETERS + [PARAMETERS[0]])
        with self.assertRaises(m.ValidationError):
            self.params([{'ParameterKey': 'VpcId', 'UsePreviousValue': True}])

    def test_invalid_admin_and_noncanonical_egress_rejected(self):
        for key, value in [('AllowedCidr', '0.0.0.0/0'), ('AllowedCidr', '999.1.2.3/32'), ('HttpsEgressCidr', '10.1.2.3/16'), ('HttpEgressCidr', '::/0')]:
            data = copy.deepcopy(PARAMETERS)
            next(p for p in data if p['ParameterKey'] == key)['ParameterValue'] = value
            with self.subTest(key=key, value=value), self.assertRaises(m.ValidationError):
                self.params(data)

    def test_template_has_one_host_no_created_network_and_exact_bootstrap(self):
        m.check_template(TEMPLATE)
        forbidden = {'AWS::EC2::VPC', 'AWS::EC2::Subnet', 'AWS::EC2::NatGateway', 'AWS::EC2::InternetGateway', 'AWS::EC2::Route', 'AWS::EC2::VPCEndpoint', 'AWS::ElasticLoadBalancingV2::LoadBalancer'}
        self.assertFalse(forbidden.intersection(r['Type'] for r in TEMPLATE['Resources'].values()))
        p = TEMPLATE['Resources']['DemoInstance']['Properties']
        self.assertEqual(p['MetadataOptions']['HttpTokens'], 'required')
        self.assertEqual(p['NetworkInterfaces'][0]['AssociatePublicIpAddress'], {'Fn::If': ['AssignPublicIp', True, False]})
        ingress = TEMPLATE['Resources']['DemoSecurityGroup']['Properties']['SecurityGroupIngress']
        self.assertEqual([(i['FromPort'], i['ToPort']) for i in ingress], [(22, 22)])

    def test_plan_reads_explicit_network_and_does_not_mutate(self):
        result = self.preflight()
        self.assertEqual(result['warnings'], [])
        self.assertEqual(result['changeSetType'], 'CREATE')
        self.assertEqual(result['network']['vpcId'], VALUES['VpcId'])
        self.assertFalse(any(op.startswith(('create-', 'execute-', 'modify-', 'update-')) for _, op, _ in self.aws.calls))
        describe_vpcs = next(args for _, op, args in self.aws.calls if op == 'describe-vpcs')
        self.assertEqual(describe_vpcs, ('--vpc-ids', VALUES['VpcId']))

    def test_subnet_mismatch_dns_and_architecture_fail(self):
        self.aws.subnet['VpcId'] = 'vpc-other'
        with self.assertRaisesRegex(m.ValidationError, 'belong'):
            self.preflight()
        self.aws.subnet['VpcId'] = VALUES['VpcId']
        self.aws.dns = False
        with self.assertRaisesRegex(m.ValidationError, 'enableDnsSupport'):
            self.preflight()
        self.aws.dns = True
        self.aws.architectures = ['x86_64']
        with self.assertRaisesRegex(m.ValidationError, 'architecture'):
            self.preflight()

    def test_wrong_ami_owner_rejected(self):
        self.aws.image['OwnerId'] = '111111111111'
        with self.assertRaisesRegex(m.ValidationError, 'Canonical'):
            self.preflight()

    def test_effective_table_explicit_then_main(self):
        main = {'RouteTableId': 'main', 'Associations': [{'Main': True}]}
        explicit = {'RouteTableId': 'explicit', 'Associations': [{'SubnetId': 'subnet-a'}]}
        self.assertEqual(m.effective_table([main, explicit], 'subnet-a')['RouteTableId'], 'explicit')
        self.assertEqual(m.effective_table([main, explicit], 'subnet-b')['RouteTableId'], 'main')

    def test_longest_prefix_catches_blackhole_hidden_by_default(self):
        blackhole = {'DestinationCidrBlock': '203.0.113.0/24', 'GatewayId': 'igw-example', 'State': 'blackhole'}
        self.assertEqual(m.route_segments([INTERNET, blackhole], '203.0.113.10/32')[0]['route']['State'], 'blackhole')
        segments = m.route_segments([INTERNET, blackhole], '0.0.0.0/0')
        self.assertTrue(any(s['route']['State'] == 'blackhole' for s in segments))
        self.assertEqual(m.route_segments([], '10.0.0.0/16')[0]['route'], None)

    def test_private_nat_and_local_admin_supported(self):
        self.values.update(AssociatePublicIpAddress='false', AllowedCidr='10.0.0.20/32')
        self.aws.routes = [LOCAL, {'DestinationCidrBlock': '0.0.0.0/0', 'NatGatewayId': 'nat-example', 'State': 'active'}]
        self.assertEqual(self.preflight()['warnings'], [])

    def test_private_transit_route_supported_without_nat_requirement(self):
        self.values.update(AssociatePublicIpAddress='false', AllowedCidr='10.0.0.20/32')
        self.aws.routes = [LOCAL, {'DestinationCidrBlock': '0.0.0.0/0', 'TransitGatewayId': 'tgw-example', 'State': 'active'}]
        result = self.preflight()
        self.assertEqual(result['warnings'], [])
        self.assertTrue(any(t.get('TransitGatewayId') for t in result['network']['targetChecks']))

    def test_private_igw_and_missing_routes_are_reported_without_network_changes(self):
        self.values.update(AssociatePublicIpAddress='false', AllowedCidr='10.0.0.20/32')
        self.assertTrue(any('IGW' in w for w in self.preflight()['warnings']))
        self.aws.routes = [LOCAL]
        self.assertTrue(any('missing' in w for w in self.preflight()['warnings']))

    def test_narrow_existing_routes_do_not_require_default(self):
        self.values.update(AssociatePublicIpAddress='false', AllowedCidr='10.0.0.20/32', HttpsEgressCidr='198.51.100.0/24', HttpEgressCidr='198.51.100.0/24')
        self.aws.routes = [LOCAL, {'DestinationCidrBlock': '198.51.100.0/24', 'TransitGatewayId': 'tgw-example', 'State': 'active'}]
        result = self.preflight()
        self.assertFalse(any('missing' in w for w in result['warnings']))
        self.assertTrue(any('restricted' in w for w in result['warnings']))

    def test_new_bootstrap_requires_http_but_existing_update_can_disable(self):
        self.values['AllowHttpEgress'] = 'false'
        with self.assertRaisesRegex(m.ValidationError, 'HTTP apt'):
            self.preflight()
        self.aws.stack = {'StackName': 'test-demo', 'StackStatus': 'UPDATE_COMPLETE'}
        self.assertEqual(self.preflight()['changeSetType'], 'UPDATE')

    def test_historical_and_unrelated_stacks_are_rejected(self):
        self.aws.stack = {'StackName': 'test-demo', 'StackStatus': 'UPDATE_COMPLETE'}
        self.aws.template['Resources']['DemoArmInstance'] = {}
        with self.assertRaisesRegex(m.ValidationError, 'historical'):
            self.preflight()
        del self.aws.template['Resources']['DemoArmInstance']
        self.aws.template['Metadata'].pop('PortableDemoVersion')
        with self.assertRaisesRegex(m.ValidationError, 'not a portable-demo'):
            self.preflight()

    def test_review_in_progress_has_create_semantics_and_no_get_template(self):
        self.aws.stack = {'StackName': 'test-demo', 'StackStatus': 'REVIEW_IN_PROGRESS'}
        self.assertEqual(self.preflight()['changeSetType'], 'CREATE')
        self.assertFalse(any(op == 'get-template' for _, op, _ in self.aws.calls))

    def test_pending_create_and_replacement_still_require_http(self):
        self.values['AllowHttpEgress'] = 'false'
        self.aws.stack = {'StackName': 'test-demo', 'StackStatus': 'REVIEW_IN_PROGRESS'}
        with self.assertRaisesRegex(m.ValidationError, 'HTTP apt'):
            self.preflight()
        self.aws.change['Parameters'] = m.parameter_list(self.values)
        self.aws.change['Changes'] = [{'ResourceChange': {'LogicalResourceId': 'DemoInstance', 'Action': 'Modify', 'Replacement': 'Conditional'}}]
        with self.assertRaisesRegex(m.ValidationError, 'fresh bootstrap'):
            m.checked_change_set(self.aws, ARN, 'test-demo', self.values, TEMPLATE, True)

    def test_nat_administration_path_needs_review(self):
        self.aws.routes = [LOCAL, {'DestinationCidrBlock': '0.0.0.0/0', 'NatGatewayId': 'nat-example', 'State': 'active'}]
        self.assertTrue(any('incoming SSH' in w for w in self.preflight()['warnings']))

    def test_execute_binds_template_parameters_stack_and_status(self):
        self.assertEqual(m.checked_change_set(self.aws, ARN, 'test-demo', VALUES, TEMPLATE, False)['Status'], 'CREATE_COMPLETE')
        self.aws.change['Parameters'][0]['ParameterValue'] = 'vpc-other'
        with self.assertRaisesRegex(m.ValidationError, 'parameters differ'):
            m.checked_change_set(self.aws, ARN, 'test-demo', VALUES, TEMPLATE, False)
        self.aws.change['Parameters'] = copy.deepcopy(PARAMETERS)
        self.aws.template['Description'] = 'changed'
        with self.assertRaisesRegex(m.ValidationError, 'template differs'):
            m.checked_change_set(self.aws, ARN, 'test-demo', VALUES, TEMPLATE, False)

    def test_replacement_and_removal_require_explicit_acknowledgement(self):
        for change in ({'Action': 'Modify', 'Replacement': 'Conditional'}, {'Action': 'Remove'}):
            self.aws.change['Changes'] = [{'ResourceChange': change}]
            with self.assertRaisesRegex(m.ValidationError, 'replace'):
                m.checked_change_set(self.aws, ARN, 'test-demo', VALUES, TEMPLATE, False)
            m.checked_change_set(self.aws, ARN, 'test-demo', VALUES, TEMPLATE, True)

    def test_mutation_requires_apply_and_create_does_not_execute(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'params.json'
            path.write_text(json.dumps(PARAMETERS))
            base = ['--parameters', str(path), '--stack-name', 'test-demo']
            with patch.object(m, 'Aws', return_value=self.aws), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(['create-change-set'] + base), 2)
                self.assertEqual(self.aws.calls, [])
                self.assertEqual(m.main(['create-change-set', '--apply'] + base), 0)
            self.assertTrue(any(op == 'create-change-set' for _, op, _ in self.aws.calls))
            self.assertFalse(any(op == 'execute-change-set' for _, op, _ in self.aws.calls))

    def test_private_route_warning_stops_apply_until_acknowledged(self):
        data = copy.deepcopy(PARAMETERS)
        next(p for p in data if p['ParameterKey'] == 'AssociatePublicIpAddress')['ParameterValue'] = 'false'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'params.json'
            path.write_text(json.dumps(data))
            base = ['create-change-set', '--apply', '--parameters', str(path), '--stack-name', 'test-demo']
            with patch.object(m, 'Aws', return_value=self.aws), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(base), 2)
                self.assertFalse(any(op == 'create-change-set' for _, op, _ in self.aws.calls))
                self.assertEqual(m.main(base + ['--acknowledge-network-review']), 0)


if __name__ == '__main__':
    unittest.main()
