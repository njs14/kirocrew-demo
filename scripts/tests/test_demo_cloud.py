"""Cloud-operation guards with generated fixtures only; no AWS or app access."""
from __future__ import annotations

import argparse
import contextlib
import copy
import importlib.util
import io
import json
import plistlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import demo_config
spec = importlib.util.spec_from_file_location("demo_cloud", SCRIPTS / "demo-cloud.py")
cloud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cloud)


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfg = demo_config.defaults()
        self.cfg["_config_path"] = str(self.root / "demo.json")
        self.cfg["aws"].update(account_id="123456789012", stack_name="portable-demo", evidence_dir=str(self.root))
        self.cfg["ssh"].update(config_path=str(self.root / "ssh-config"), known_hosts_path=str(self.root / "pins"),
                               host_key_alias="portable-host", gateway_alias="portable-crew", admin_alias="portable-admin",
                               aliases=["portable-crew", "portable-admin"])
        self.cfg["client"]["config_path"] = str(self.root / "client.json")
        self.arn = "arn:aws:cloudformation:us-east-1:123456789012:stack/portable-demo/00000000-0000-0000-0000-000000000000"
        self.instance_id = "i-0123456789abcdef0"
        self.stack = {"StackName": "portable-demo", "StackId": self.arn, "StackStatus": "UPDATE_COMPLETE",
                      "Outputs": [{"OutputKey": k, "OutputValue": v} for k, v in
                                  {"InstanceId": self.instance_id, "SecurityGroupId": "sg-0123456789abcdef0", "DemoBucketName": "portable-fixture"}.items()],
                      "Parameters": [{"ParameterKey": k, "ParameterValue": v} for k, v in
                                     {"AllowedCidr": "1.1.1.1/32", "VpcId": "vpc-0123456789abcdef0", "SubnetId": "subnet-0123456789abcdef0"}.items()]}
        self.tags = [{"Key": "Project", "Value": "kirocrew-demo"}, {"Key": "aws:cloudformation:stack-id", "Value": self.arn}]
        self.instance = {"InstanceId": self.instance_id, "InstanceType": "t4g.xlarge", "Architecture": "arm64",
                         "State": {"Name": "running"}, "PublicIpAddress": "8.8.8.8", "PrivateIpAddress": "10.1.2.3",
                         "VpcId": "vpc-0123456789abcdef0", "SubnetId": "subnet-0123456789abcdef0",
                         "SecurityGroups": [{"GroupId": "sg-0123456789abcdef0"}], "Tags": copy.deepcopy(self.tags)}
        self.group = {"GroupId": "sg-0123456789abcdef0", "VpcId": self.instance["VpcId"], "Tags": copy.deepcopy(self.tags),
                      "IpPermissions": [{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "1.1.1.1/32"}]}]}
        self.args = argparse.Namespace(config=self.cfg, offline=False, evidence_dir=None, apply=False, profile=None, client_ip=None)
        self.source = ("# unrelated config\nHost unrelated\n  HostName keep.example\n\n"
                       "Host portable-crew portable-admin\n  HostName 8.8.4.4 # preserve comment\n"
                       "  StrictHostKeyChecking yes\n  HostKeyAlias portable-host\n  IdentitiesOnly yes\n"
                       f"  UserKnownHostsFile {self.root / 'pins'}\n  ProxyJump existing-bastion\n"
                       "Host portable-crew\n  User crew\nHost portable-admin\n  User ubuntu\n")

    def fake_aws(self, args, service, operation, **payload):
        if service == "sts":
            return {"Account": "123456789012"}
        if operation == "describe-stacks":
            return {"Stacks": [copy.deepcopy(self.stack)]}
        if operation == "describe-instances":
            self.assertEqual(payload, {"InstanceIds": [self.instance_id]})
            return {"Reservations": [{"Instances": [copy.deepcopy(self.instance)]}]}
        if operation == "describe-security-groups":
            self.assertEqual(payload, {"GroupIds": [self.group["GroupId"]]})
            return {"SecurityGroups": [copy.deepcopy(self.group)]}
        self.fail("Unexpected AWS operation: " + operation)

    def context(self):
        with patch.object(cloud, "aws", side_effect=self.fake_aws):
            return cloud.get_context(self.args)

    def invoke_main(self, argv, **overrides):
        defaults = {"load_config": self.cfg, "get_context": self.context(), "check_local_files": self.source,
                    "current_client_ip": "1.1.1.1"}
        defaults.update(overrides)
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(sys, "argv", ["demo-cloud.py", *argv]))
            stack.enter_context(patch.object(cloud.shutil, "which", return_value="/usr/bin/aws"))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            mocks = {}
            for name, result in defaults.items():
                mocks[name] = stack.enter_context(patch.object(cloud, name, side_effect=result if isinstance(result, Exception) else None,
                                                               return_value=None if isinstance(result, Exception) else result))
            return cloud.main(), mocks

    def test_explicit_config_required_before_aws(self):
        with patch.dict(cloud.os.environ, {}, clear=True), patch.object(sys, "argv", ["demo-cloud.py", "status"]), patch.object(cloud, "aws") as aws:
            with self.assertRaisesRegex(ValueError, "Choose the deployment explicitly"):
                cloud.main()
            aws.assert_not_called()

    def test_named_stack_discovers_outputs_without_fixed_instance(self):
        context = self.context()
        self.assertEqual(context["instance"]["InstanceId"], self.instance_id)
        self.assertEqual(context["outputs"]["DemoBucketName"], "portable-fixture")

    def test_account_mismatch_prevents_stack_discovery(self):
        with patch.object(cloud, "aws", return_value={"Account": "999999999999"}) as aws:
            with self.assertRaisesRegex(RuntimeError, "account differs"):
                cloud.get_context(self.args)
            self.assertEqual(aws.call_count, 1)

    def test_stack_arn_account_region_name_and_optional_pin(self):
        for old, new in (("123456789012", "999999999999"), ("us-east-1", "us-west-2"), ("portable-demo/", "another-demo/")):
            with self.subTest(new=new):
                other = dict(self.stack, StackId=self.arn.replace(old, new))
                with self.assertRaises(RuntimeError):
                    cloud.validate_stack_binding(other, self.cfg)
        self.cfg["aws"]["stack_arn"] = self.arn[:-1] + "1"
        with self.assertRaisesRegex(RuntimeError, "Configured stack ARN"):
            self.context()

    def test_optional_instance_pins_are_enforced(self):
        for key, wrong in (("instance_id", "i-00000000000000000"), ("instance_type", "t3.small"), ("architecture", "x86_64")):
            with self.subTest(key=key):
                config = copy.deepcopy(self.cfg)
                config["aws"][key] = wrong
                with self.assertRaisesRegex(RuntimeError, key):
                    cloud.validate_instance_binding(self.instance, self.instance_id, config)

    def test_cloudformation_ownership_tags_are_required(self):
        for target in (self.instance, self.group):
            saved = copy.deepcopy(target["Tags"])
            target["Tags"] = [x for x in saved if x["Key"] != "aws:cloudformation:stack-id"]
            with self.assertRaisesRegex(RuntimeError, "not owned"):
                self.context()
            target["Tags"] = saved

    def test_attachment_and_placement_drift_rejected(self):
        for resource, key, value in ((self.group, "VpcId", "vpc-other"), (self.instance, "SubnetId", "subnet-other"),
                                     (self.instance, "SecurityGroups", [{"GroupId": "sg-other"}])):
            saved = resource[key]
            resource[key] = value
            with self.assertRaises(RuntimeError):
                self.context()
            resource[key] = saved

    def test_ingress_only_one_ssh_ipv4_host(self):
        variants = [[], self.group["IpPermissions"] * 2,
                    [dict(self.group["IpPermissions"][0], FromPort=80)],
                    [dict(self.group["IpPermissions"][0], IpRanges=[{"CidrIp": "0.0.0.0/0"}])],
                    [dict(self.group["IpPermissions"][0], Ipv6Ranges=[{"CidrIpv6": "::/0"}])]]
        for rules in variants:
            with self.subTest(rules=rules), self.assertRaises(RuntimeError):
                cloud.ingress_cidr(dict(self.group, IpPermissions=rules))
        self.stack["Parameters"][0]["ParameterValue"] = "8.8.8.8/32"
        with self.assertRaisesRegex(RuntimeError, "live ingress differ"):
            self.context()

    def test_offline_evidence_directory_and_bindings(self):
        (self.root / "stack-state.json").write_text(json.dumps({"Stacks": [self.stack]}))
        (self.root / "instance.json").write_text(json.dumps({"Reservations": [{"Instances": [self.instance]}]}))
        (self.root / "security-group.json").write_text(json.dumps({"SecurityGroups": [self.group]}))
        self.args.offline = True
        self.args.evidence_dir = str(self.root)
        with patch.object(cloud, "aws") as aws:
            self.assertEqual(cloud.get_context(self.args)["instance"]["InstanceId"], self.instance_id)
            aws.assert_not_called()
        self.cfg["aws"]["instance_id"] = "i-00000000000000000"
        with self.assertRaisesRegex(RuntimeError, "instance_id"):
            cloud.get_context(self.args)

    def test_offline_apply_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "cannot be combined"):
            self.invoke_main(["start", "--offline", "--apply"])

    def test_private_address_selection_and_public_requirement(self):
        self.cfg["ssh"]["address_mode"] = "private"
        self.assertEqual(cloud.instance_address(self.instance, self.cfg), "10.1.2.3")
        self.instance.pop("PublicIpAddress")
        self.cfg["ssh"]["address_mode"] = "auto"
        self.assertEqual(cloud.instance_address(self.instance, self.cfg), "10.1.2.3")
        self.cfg["ssh"]["address_mode"] = "public"
        with self.assertRaisesRegex(RuntimeError, "No public"):
            cloud.instance_address(self.instance, self.cfg)

    def test_private_route_requires_explicit_source_not_public_discovery(self):
        self.cfg["ssh"]["address_mode"] = "private"
        context = self.context()
        with patch.object(cloud.urllib.request, "build_opener") as opener:
            with self.assertRaisesRegex(RuntimeError, "requires --client-ip"):
                cloud.current_client_ip(self.args, context)
            opener.assert_not_called()
        self.args.client_ip = "10.8.0.10"
        self.assertEqual(cloud.current_client_ip(self.args, context), "10.8.0.10")
        self.cfg["ssh"]["address_mode"] = "public"
        with self.assertRaisesRegex(RuntimeError, "globally routable"):
            cloud.current_client_ip(self.args, context)

    def test_private_ssh_edit_preserves_other_bytes_and_proxyjump(self):
        edited, before = cloud.ssh_update_text(self.source, "10.1.2.3", self.cfg)
        self.assertEqual(before, "8.8.4.4")
        self.assertEqual(edited, self.source.replace("HostName 8.8.4.4", "HostName 10.1.2.3"))

    def test_ssh_guard_changes_and_ambiguous_blocks_are_rejected(self):
        for source in (self.source.replace("StrictHostKeyChecking yes", "StrictHostKeyChecking no"),
                       self.source.replace("HostKeyAlias portable-host", "HostKeyAlias other"),
                       self.source.replace("IdentitiesOnly yes", "IdentitiesOnly no"),
                       self.source.replace(str(self.root / "pins"), "/tmp/other"),
                       self.source.replace("Host portable-crew portable-admin", "Host portable-crew portable-admin extra"),
                       self.source + self.source,
                       self.source.replace("  HostName 8.8.4.4", "  HostName 10.0.0.1\n  HostName 8.8.4.4")):
            with self.subTest(source=source), self.assertRaises(RuntimeError):
                cloud.ssh_update_text(source, "10.1.2.3", self.cfg)

    def test_atomic_write_keeps_private_backup_and_rejects_changed_source(self):
        path = self.root / "config"
        path.write_bytes(b"original")
        backup = cloud.atomic_backup_write(path, b"original", b"changed")
        self.assertEqual(path.read_bytes(), b"changed")
        self.assertEqual(backup.read_bytes(), b"original")
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        with self.assertRaisesRegex(RuntimeError, "changed during"):
            cloud.atomic_backup_write(path, b"original", b"again")
        link = self.root / "link"
        link.symlink_to(path)
        with self.assertRaisesRegex(RuntimeError, "nonregular"):
            cloud.atomic_backup_write(link, b"changed", b"again")

    def test_linux_manual_tunnel_never_uses_launchctl(self):
        Path(self.cfg["ssh"]["config_path"]).write_text(self.source)
        Path(self.cfg["ssh"]["known_hosts_path"]).write_text("test fixture")
        with patch.object(cloud.sys, "platform", "linux"), patch.object(cloud, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            self.assertEqual(cloud.check_local_files(self.args), self.source)
            with contextlib.redirect_stdout(io.StringIO()) as out:
                cloud.tunnel(self.args, True, apply=True)
                cloud.tunnel(self.args, False, apply=True)
            self.assertIn("127.0.0.1:5599:127.0.0.1:5476", out.getvalue())
            self.assertEqual([x.args[0][0] for x in run.call_args_list], ["ssh-keygen"])

    def launch_result(self, *, argv=None, program=None, absent=False):
        label = self.cfg["tunnel"]["launch_label"]
        target = f"gui/{cloud.os.getuid()}/{label}"
        if absent:
            return subprocess.CompletedProcess([], 113, "", f'Bad request.\nCould not find service "{label}" in domain for user gui: {cloud.os.getuid()}\n')
        argv = argv or cloud.tunnel_command(self.args)
        program = program or argv[0]
        output = target + " = {\n\tprogram = " + program + "\n\targuments = {\n"
        output += "".join("\t\t" + item + "\n" for item in argv) + "\t}\n}\n"
        return subprocess.CompletedProcess([], 0, output, "")

    def test_unrelated_loaded_tunnel_rejected_before_mutation(self):
        self.cfg["tunnel"]["mode"] = "launchagent"
        for restart in (True, False):
            for result in (self.launch_result(program="/bin/unrelated"),
                           self.launch_result(argv=["/usr/bin/ssh", "unrelated-host"])):
                with self.subTest(restart=restart), patch.object(cloud.sys, "platform", "darwin"), \
                     patch.object(cloud, "run", return_value=result) as run:
                    with self.assertRaisesRegex(RuntimeError, "Loaded tunnel LaunchAgent command differs"):
                        cloud.tunnel(self.args, restart, apply=True)
                    self.assertEqual([call.args[0][1] for call in run.call_args_list], ["print"])

    def test_exact_loaded_tunnel_allows_only_requested_action(self):
        self.cfg["tunnel"]["mode"] = "launchagent"
        for restart, action in ((True, "kickstart"), (False, "bootout")):
            with self.subTest(action=action), patch.object(cloud.sys, "platform", "darwin"), \
                 patch.object(cloud, "run", side_effect=[self.launch_result(), subprocess.CompletedProcess([], 0, "", "")]) as run:
                cloud.tunnel(self.args, restart, apply=True)
                self.assertEqual([call.args[0][1] for call in run.call_args_list], ["print", action])

    def test_only_exact_absence_allows_bootstrap_with_matching_plist(self):
        self.cfg["tunnel"]["mode"] = "launchagent"
        path = self.root / "tunnel.plist"
        self.cfg["tunnel"]["launch_plist_path"] = str(path)
        path.write_bytes(plistlib.dumps({"Label": self.cfg["tunnel"]["launch_label"],
                                        "ProgramArguments": cloud.tunnel_command(self.args)}))
        with patch.object(cloud.sys, "platform", "darwin"), \
             patch.object(cloud, "run", side_effect=[self.launch_result(absent=True), subprocess.CompletedProcess([], 0, "", "")]) as run:
            cloud.tunnel(self.args, True, apply=True)
            self.assertEqual([call.args[0][1] for call in run.call_args_list], ["print", "bootstrap"])
        definition = plistlib.loads(path.read_bytes())
        definition["Program"] = "/bin/unrelated"
        path.write_bytes(plistlib.dumps(definition))
        with patch.object(cloud.sys, "platform", "darwin"), patch.object(cloud, "run", return_value=self.launch_result(absent=True)) as run:
            with self.assertRaisesRegex(RuntimeError, "LaunchAgent command changed"):
                cloud.tunnel(self.args, True, apply=True)
            self.assertEqual([call.args[0][1] for call in run.call_args_list], ["print"])

    def test_unknown_launchctl_state_and_oversized_output_fail_closed(self):
        self.cfg["tunnel"]["mode"] = "launchagent"
        absent = self.launch_result(absent=True)
        variants = [subprocess.CompletedProcess([], 1, "", "permission denied"),
                    subprocess.CompletedProcess([], 113, "", absent.stderr.replace(self.cfg["tunnel"]["launch_label"], "another-label")),
                    subprocess.CompletedProcess([], 113, "", absent.stderr + "unexpected error\n"),
                    subprocess.CompletedProcess([], 0, "x" * 65537, ""),
                    subprocess.CompletedProcess([], 0, self.launch_result().stdout, "x" * 65537)]
        for result in variants:
            with self.subTest(result=result.returncode), patch.object(cloud.sys, "platform", "darwin"), \
                 patch.object(cloud, "run", return_value=result) as run:
                with self.assertRaises(RuntimeError):
                    cloud.tunnel(self.args, True, apply=True)
                self.assertEqual([call.args[0][1] for call in run.call_args_list], ["print"])

    def test_rollback_rejects_unrelated_loaded_job_without_ssh_preflight(self):
        self.cfg["tunnel"]["mode"] = "launchagent"
        self.cfg["client"]["process_pattern"] = "^/fixture/client$"
        path = Path(self.cfg["client"]["config_path"])
        original = b'{"runLocalGateway": false, "remoteHosts": {}}'
        path.write_bytes(original)
        self.args.apply = True
        with patch.object(cloud.sys, "platform", "darwin"), \
             patch.object(cloud, "run", side_effect=[subprocess.CompletedProcess([], 1, "", ""), self.launch_result(program="/bin/unrelated")]) as run, \
             patch.object(cloud, "atomic_backup_write") as write, patch.object(cloud, "check_local_files") as check, \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "Loaded tunnel LaunchAgent command differs"):
                cloud.restore_local_client(self.args)
            check.assert_not_called()
            write.assert_not_called()
            self.assertEqual([call.args[0][0] for call in run.call_args_list], ["pgrep", "/bin/launchctl"])
            self.assertEqual(path.read_bytes(), original)

    def test_wait_running_accepts_private_only_and_preserves_instance_pin(self):
        self.instance.pop("PublicIpAddress")
        with patch.object(cloud, "aws", side_effect=self.fake_aws), patch.object(cloud.time, "sleep") as sleep, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cloud.wait_instance(self.args, "running", self.instance_id)["PrivateIpAddress"], "10.1.2.3")
            sleep.assert_not_called()

    def test_cidr_update_changes_one_parameter_and_binds_stack_arn(self):
        context = self.context()
        self.args.apply = True
        updated = copy.deepcopy(context)
        updated["cidr"] = "8.8.4.4/32"
        calls = []
        def aws(args, service, operation, **payload):
            calls.append((operation, payload))
            return {"Stacks": [self.stack]} if operation == "describe-stacks" else {}
        with patch.object(cloud, "aws", side_effect=aws), patch.object(cloud, "get_context", return_value=updated), contextlib.redirect_stdout(io.StringIO()):
            cloud.update_cidr(self.args, context, "8.8.4.4/32")
        update = calls[0][1]
        self.assertEqual(update["StackName"], self.arn)
        self.assertTrue(update["UsePreviousTemplate"])
        self.assertEqual(update["Parameters"], [{"ParameterKey": "AllowedCidr", "ParameterValue": "8.8.4.4/32"},
                                               {"ParameterKey": "VpcId", "UsePreviousValue": True},
                                               {"ParameterKey": "SubnetId", "UsePreviousValue": True}])

    def test_failed_ingress_prevents_instance_start_and_local_mutation(self):
        self.instance["State"]["Name"] = "stopped"
        with patch.object(cloud, "aws") as aws, patch.object(cloud, "atomic_backup_write") as write, patch.object(cloud, "tunnel") as tunnel:
            with self.assertRaisesRegex(RuntimeError, "update failed"):
                self.invoke_main(["start", "--apply"], update_cidr=RuntimeError("update failed"))
            aws.assert_not_called()
            write.assert_not_called()
            tunnel.assert_not_called()

    def test_start_occurs_after_cidr_verification(self):
        self.instance["State"]["Name"] = "stopped"
        events = []
        running = dict(self.instance, State={"Name": "running"})
        with patch.object(cloud, "update_cidr", side_effect=lambda *args: events.append("verified ingress")), \
             patch.object(cloud, "aws", side_effect=lambda *args, **kw: events.append("start")), \
             patch.object(cloud, "atomic_backup_write", return_value=None), patch.object(cloud, "tunnel"):
            code, _ = self.invoke_main(["start", "--apply"], wait_instance=running)
        self.assertEqual(code, 0)
        self.assertEqual(events, ["verified ingress", "start"])

    def test_dry_run_does_not_mutate_aws_ssh_or_tunnel(self):
        with patch.object(cloud, "aws") as aws, patch.object(cloud, "atomic_backup_write") as write, patch.object(cloud, "run") as run:
            code, _ = self.invoke_main(["start", "--dry-run"])
            self.assertEqual(code, 0)
            aws.assert_not_called()
            write.assert_not_called()
            run.assert_not_called()

    def test_rollback_targets_configured_port_and_requires_matching_pair(self):
        self.cfg["ssh"]["local_port"] = 6000
        path = Path(self.cfg["client"]["config_path"])
        value = {"runLocalGateway": False, "other": {"preserve": 1}, "remoteHosts": {
            "6000": {"host": "portable-admin", "binPath": "/usr/local/bin/kirocrew-owner-token"},
            "5599": {"host": "unrelated", "binPath": "unrelated"}}}
        path.write_text(json.dumps(value))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            cloud.restore_local_client(self.args)
        self.assertIn("remoteHosts[6000]", out.getvalue())
        self.assertEqual(json.loads(path.read_text()), value)
        value["remoteHosts"]["6000"]["host"] = "unrelated"
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(RuntimeError, "refusing removal"):
            cloud.restore_local_client(self.args)


if __name__ == "__main__":
    unittest.main()
