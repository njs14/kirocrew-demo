#!/usr/bin/env python3
"""Operate the existing KiroCrew demo; mutations require --apply.

Python's standard library is used for strict JSON/IP validation and atomic local
configuration updates. AWS operations use the existing AWS CLI credential chain.
No credentials or SSH keys are copied, printed, or rewritten.
"""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import os
from pathlib import Path
import plistlib
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request

from demo_config import load_config

def setting(args: argparse.Namespace, section: str, name: str):
    return args.config[section][name]


def tunnel_command(args: argparse.Namespace) -> list[str]:
    ssh = args.config["ssh"]
    command = ["/usr/bin/ssh" if args.config["tunnel"]["mode"] == "launchagent" else "ssh",
               "-F", ssh["config_path"], "-N", "-T", "-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=yes"]
    if args.config["tunnel"]["mode"] == "manual":
        command += ["-o", "StrictHostKeyChecking=yes", "-o", "HostKeyAlias=" + ssh["host_key_alias"],
                    "-o", "UserKnownHostsFile=" + ssh["known_hosts_path"], "-o", "IdentitiesOnly=yes",
                    "-o", "ForwardAgent=no"]
    return command + ["-L", f"127.0.0.1:{ssh['local_port']}:127.0.0.1:{ssh['remote_port']}", ssh["gateway_alias"]]


def require(condition: object, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(argv: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True, timeout=timeout,
                          env={**os.environ, "AWS_PAGER": "", "AWS_CLI_AUTO_PROMPT": "off"})


def aws(args: argparse.Namespace, service: str, operation: str, **payload: object) -> dict:
    command = ["aws", "--region", setting(args, "aws", "region"), "--output", "json", "--no-cli-pager"]
    profile = args.profile or args.config["aws"].get("profile")
    if profile:
        command += ["--profile", profile]
    command += [service, operation]
    if payload:
        command += ["--cli-input-json", json.dumps(payload)]
    result = run(command)
    require(result.returncode == 0,
            f"AWS {service} {operation} failed: {result.stderr.strip()}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def ingress_cidr(group: dict) -> str:
    rules = group.get("IpPermissions", [])
    require(len(rules) == 1, "Security group must have exactly one inbound rule.")
    rule = rules[0]
    require(rule.get("IpProtocol") == "tcp" and rule.get("FromPort") == 22
            and rule.get("ToPort") == 22, "Only inbound TCP 22 is accepted.")
    require(not rule.get("Ipv6Ranges") and not rule.get("UserIdGroupPairs")
            and not rule.get("PrefixListIds"), "Unexpected non-IPv4 ingress source.")
    ranges = rule.get("IpRanges", [])
    require(len(ranges) == 1, "Exactly one inbound IPv4 /32 is required.")
    network = ipaddress.ip_network(ranges[0]["CidrIp"], strict=True)
    require(network.version == 4 and network.prefixlen == 32, "Inbound CIDR must be /32.")
    return str(network)


def validate_instance_binding(instance: dict, instance_id: str, config: dict) -> None:
    require(instance.get("InstanceId") == instance_id, "Instance response does not match the stack output.")
    expected = config["aws"]
    for key, field in (("instance_id", "InstanceId"), ("instance_type", "InstanceType"),
                       ("architecture", "Architecture")):
        if expected.get(key):
            require(instance.get(field) == expected[key], f"Configured AWS {key} binding does not match.")


def validate_stack_binding(stack: dict, config: dict) -> None:
    expected = config["aws"]
    require(stack.get("StackName") == expected["stack_name"], "Unexpected CloudFormation stack name.")
    arn = stack.get("StackId", "")
    match = re.fullmatch(r"arn:(aws(?:-[a-z-]+)?):cloudformation:([^:]+):(\d{12}):stack/([^/]+)/([^/]+)", arn)
    require(match and match[2] == expected["region"] and match[3] == expected["account_id"]
            and match[4] == expected["stack_name"], "Stack ARN does not match the configured account, region and name.")
    require(not expected.get("stack_arn") or arn == expected["stack_arn"], "Configured stack ARN binding does not match.")


def get_context(args: argparse.Namespace) -> dict:
    cfg = args.config
    if args.offline:
        evidence = Path(args.evidence_dir or cfg["aws"]["evidence_dir"])
        stack = json.loads((evidence / "stack-state.json").read_text())["Stacks"][0]
    else:
        identity = aws(args, "sts", "get-caller-identity")
        require(identity.get("Account") == cfg["aws"]["account_id"], "AWS account differs from the configured account.")
        stack = aws(args, "cloudformation", "describe-stacks", StackName=cfg["aws"]["stack_name"])["Stacks"][0]
    validate_stack_binding(stack, cfg)
    outputs = {x["OutputKey"]: x["OutputValue"] for x in stack["Outputs"]}
    instance_id = outputs["InstanceId"]
    if args.offline:
        instance_data = json.loads((evidence / "instance.json").read_text())
        group_data = json.loads((evidence / "security-group.json").read_text())
        instances = [item for reservation in instance_data["Reservations"] for item in reservation["Instances"]]
        groups = group_data["SecurityGroups"]
    else:
        instances = [item for reservation in aws(args, "ec2", "describe-instances", InstanceIds=[instance_id])["Reservations"]
                     for item in reservation["Instances"]]
        groups = aws(args, "ec2", "describe-security-groups", GroupIds=[outputs["SecurityGroupId"]])["SecurityGroups"]
    require(len(instances) == 1 and len(groups) == 1, "Expected exactly one stack instance and security group.")
    instance, group = instances[0], groups[0]
    validate_instance_binding(instance, instance_id, cfg)
    require([g["GroupId"] for g in instance.get("SecurityGroups", [])] == [group["GroupId"]]
            and group["GroupId"] == outputs["SecurityGroupId"], "Instance security-group attachment changed.")
    require(instance.get("VpcId") == group.get("VpcId") and bool(instance.get("VpcId")),
            "Instance and security group must belong to the same VPC.")
    for resource in (instance, group):
        tags = {x["Key"]: x["Value"] for x in resource.get("Tags", [])}
        require(tags.get("Project") == cfg["aws"]["project_tag"], "Project resource tag does not match.")
        require(tags.get("aws:cloudformation:stack-id") == stack["StackId"],
                "Resource is not owned by the selected CloudFormation stack.")
    cidr = ingress_cidr(group)
    parameters = {p["ParameterKey"]: p["ParameterValue"] for p in stack["Parameters"]}
    keys = [key for key in ("AllowedCidr", "ClientCidr") if key in parameters]
    require(len(keys) == 1, "Cannot identify exactly one existing client CIDR parameter.")
    require(parameters[keys[0]] == cidr, "CloudFormation CIDR and live ingress differ; review drift first.")
    for parameter, actual in (("VpcId", instance["VpcId"]), ("SubnetId", instance.get("SubnetId"))):
        if parameter in parameters:
            require(parameters[parameter] == actual, f"CloudFormation {parameter} and instance placement differ.")
    return {"stack": stack, "instance": instance, "group": group, "outputs": outputs,
            "cidr": cidr, "cidr_key": keys[0]}


def public_ip(value: str) -> str:
    address = ipaddress.ip_address(value.strip())
    require(address.version == 4 and address.is_global, "A globally routable public IPv4 address is required.")
    return str(address)


def current_client_ip(args: argparse.Namespace, context: dict) -> str:
    private_route = (args.config["ssh"]["address_mode"] == "private"
                     or (args.config["ssh"]["address_mode"] == "auto"
                         and not context["instance"].get("PublicIpAddress")))
    if args.client_ip:
        return ssh_ip(args.client_ip) if private_route else public_ip(args.client_ip)
    if args.offline:
        return context["cidr"].split("/")[0]
    require(not private_route, "Private SSH routing requires --client-ip with the IPv4 source seen by EC2; public egress discovery cannot determine it.")
    # Disable proxy environment settings: this is the machine's direct egress IP.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open("https://checkip.amazonaws.com", timeout=15) as response:
        require(response.geturl() == "https://checkip.amazonaws.com", "Unexpected public-IP discovery redirect.")
        return public_ip(response.read(64).decode("ascii"))


def ssh_ip(value: str) -> str:
    address = ipaddress.ip_address(value.strip())
    require(address.version == 4 and not address.is_unspecified and not address.is_multicast
            and not address.is_loopback and not address.is_link_local,
            "SSH target must be a unicast public or private IPv4 address.")
    return str(address)


def instance_address(instance: dict, config: dict) -> str:
    mode = config["ssh"]["address_mode"]
    if mode == "public":
        require(instance.get("PublicIpAddress"), "No public instance IPv4; use private mode with an existing route.")
        return public_ip(instance["PublicIpAddress"])
    if mode == "private":
        require(instance.get("PrivateIpAddress"), "Instance has no private IPv4 address.")
        return ssh_ip(instance["PrivateIpAddress"])
    require(mode == "auto", "Unsupported SSH address mode.")
    value = instance.get("PublicIpAddress") or instance.get("PrivateIpAddress")
    require(value, "Instance has no IPv4 SSH target.")
    return ssh_ip(value)


def ssh_update_text(source: str, address: str, config: dict) -> tuple[str, str]:
    """Change one HostName in the exact shared alias block, leaving other bytes intact."""
    address = ssh_ip(address)
    ssh = config["ssh"]
    aliases = set(ssh["aliases"])
    lines = source.splitlines(keepends=True)
    starts = []
    for index, line in enumerate(lines):
        tokens = shlex.split(line, comments=True)
        if tokens and tokens[0].lower() == "host" and set(tokens[1:]) == aliases:
            starts.append(index)
    require(len(starts) == 1, "Expected exactly one shared SSH Host block containing the configured aliases.")
    start = starts[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        tokens = shlex.split(lines[index], comments=True)
        if tokens and tokens[0].lower() in ("host", "match"):
            end = index
            break
    fields: dict[str, list[tuple[int, list[str]]]] = {}
    for index in range(start + 1, end):
        tokens = shlex.split(lines[index], comments=True)
        if tokens:
            fields.setdefault(tokens[0].lower(), []).append((index, tokens[1:]))
    required = {"stricthostkeychecking": "yes", "hostkeyalias": ssh["host_key_alias"],
                "identitiesonly": "yes"}
    for key, value in required.items():
        require(len(fields.get(key, [])) == 1 and fields[key][0][1] == [value],
                f"Preserved SSH guard differs: {key}.")
    known = fields.get("userknownhostsfile", [])
    require(len(known) == 1 and len(known[0][1]) == 1
            and Path(known[0][1][0]).expanduser() == Path(ssh["known_hosts_path"]),
            "SSH must keep the dedicated pinned known-hosts file.")
    require(len(fields.get("hostname", [])) == 1, "Expected exactly one shared HostName.")
    index, old = fields["hostname"][0]
    require(len(old) == 1, "Unexpected HostName syntax.")
    match = re.fullmatch(r"(\s*HostName\s+)(\S+)([^\r\n]*)(\r?\n)?", lines[index], re.IGNORECASE)
    require(match is not None, "Cannot preserve HostName formatting safely.")
    lines[index] = match[1] + address + match[3] + (match[4] or "")
    return "".join(lines), old[0]


def check_local_files(args: argparse.Namespace) -> str:
    ssh = args.config["ssh"]
    require(ssh["host_key_alias"], "Configure ssh.host_key_alias from the verified pinned instance host key.")
    ssh_config = Path(ssh["config_path"])
    known_hosts = Path(ssh["known_hosts_path"])
    require(ssh_config.is_file() and not ssh_config.is_symlink(), "SSH config must be a regular file.")
    require(known_hosts.is_file() and not known_hosts.is_symlink(), "Pinned known-hosts file is missing.")
    source = ssh_config.read_bytes().decode("utf-8")
    ssh_update_text(source, "10.0.0.2", args.config)  # Validate the exact block without writing it.
    key_check = run(["ssh-keygen", "-F", ssh["host_key_alias"], "-f", str(known_hosts)])
    require(key_check.returncode == 0, "Expected pinned host key alias is absent.")
    if args.config["tunnel"]["mode"] == "launchagent":
        require(sys.platform == "darwin", "LaunchAgent tunnel mode requires macOS; select manual mode on this machine.")
        check_tunnel_plist(args)
    return source


def atomic_backup_write(path: Path, original: bytes, replacement: bytes) -> Path | None:
    require(path.is_file() and not path.is_symlink(), f"Refusing to replace a nonregular file: {path}")
    require(path.read_bytes() == original, f"File changed during operation: {path}")
    if original == replacement:
        return None
    suffix = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = path.with_name(path.name + ".before-demo-cloud-" + suffix)
    with backup.open("xb") as handle:
        os.chmod(backup, 0o600)
        handle.write(original)
        handle.flush()
        os.fsync(handle.fileno())
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".demo-cloud-", delete=False) as handle:
            temporary = Path(handle.name)
            os.chmod(temporary, 0o600)
            handle.write(replacement)
            handle.flush()
            os.fsync(handle.fileno())
        require(path.read_bytes() == original, "Configuration changed after backup; original preserved.")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return backup


def check_tunnel_plist(args: argparse.Namespace) -> bytes:
    """Validate the file bootstrap would load, independently of SSH setup checks."""
    path = Path(args.config["tunnel"]["launch_plist_path"])
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o022,
            "Tunnel LaunchAgent must be a regular, user-owned file without group/other write access.")
    require(info.st_size <= 65536, "Tunnel LaunchAgent file is too large to inspect safely.")
    data = path.read_bytes()
    plist = plistlib.loads(data)
    expected = tunnel_command(args)
    require(plist.get("Label") == args.config["tunnel"]["launch_label"]
            and plist.get("ProgramArguments") == expected
            and plist.get("Program", expected[0]) == expected[0],
            "Tunnel LaunchAgent command changed; review it before restarting.")
    return data


def managed_tunnel_job(args: argparse.Namespace) -> bool:
    """Recognize only the exact loaded SSH job or an explicit absence response.

    launchctl output remains in memory and never enters receipts or errors.
    An unreadable, oversized or differently configured job cannot be adopted.
    """
    label = args.config["tunnel"]["launch_label"]
    target = f"gui/{os.getuid()}/{label}"
    result = run(["/bin/launchctl", "print", target], timeout=10)
    require(len(result.stdout) <= 65536 and len(result.stderr) <= 65536,
            "Tunnel LaunchAgent state is too large to inspect safely.")
    absent = f'Could not find service "{label}" in domain for user gui: {os.getuid()}'
    error_lines = result.stderr.splitlines()
    if (result.returncode == 113 and not result.stdout and error_lines.count(absent) == 1
            and all(line in ("Bad request.", absent) for line in error_lines)):
        return False
    require(result.returncode == 0, "Tunnel LaunchAgent state is unknown; refusing to change a job.")
    programs = re.findall(r"^[ \t]+program = (.+)$", result.stdout, re.MULTILINE)
    arguments = re.findall(r"^[ \t]+arguments = \{\n(.*?)^[ \t]+\}[ \t]*$",
                           result.stdout, re.MULTILINE | re.DOTALL)
    expected = tunnel_command(args)
    actual = [line.strip() for line in arguments[0].splitlines() if line.strip()] if len(arguments) == 1 else None
    require(result.stdout.startswith(target + " = {") and len(programs) == 1
            and programs[0].strip() == expected[0] and actual == expected,
            "Loaded tunnel LaunchAgent command differs; refusing to change this job.")
    return True


def tunnel(args: argparse.Namespace, restart: bool, *, apply: bool) -> None:
    cfg = args.config["tunnel"]
    if cfg["mode"] == "manual":
        if restart:
            print("Manual tunnel: run this command in a separate terminal after the host is ready:")
            print(shlex.join(tunnel_command(args)))
        else:
            print("Manual tunnel: stop the SSH forwarding process you started (Ctrl-C in its terminal).")
        return
    require(cfg["mode"] == "launchagent" and sys.platform == "darwin", "LaunchAgent tunnel mode requires macOS.")
    target = f"gui/{os.getuid()}/{cfg['launch_label']}"
    if not apply:
        print(f"Would {'restart' if restart else 'unload'} local tunnel {target}.")
        return
    loaded = managed_tunnel_job(args)
    if restart:
        if not loaded:
            previous = check_tunnel_plist(args)
            require(Path(cfg["launch_plist_path"]).read_bytes() == previous,
                    "Tunnel LaunchAgent file changed before bootstrap.")
        command = (["/bin/launchctl", "kickstart", "-k", target] if loaded else
                   ["/bin/launchctl", "bootstrap", f"gui/{os.getuid()}", cfg["launch_plist_path"]])
        result = run(command)
        require(result.returncode == 0, f"Tunnel restart failed: {result.stderr.strip()}")
    elif loaded:
        result = run(["/bin/launchctl", "bootout", target])
        require(result.returncode == 0, f"Tunnel unload failed: {result.stderr.strip()}")


def wait_instance(args: argparse.Namespace, desired: str, instance_id: str) -> dict:
    deadline = time.monotonic() + 600
    previous = None
    while time.monotonic() < deadline:
        instance = aws(args, "ec2", "describe-instances", InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
        validate_instance_binding(instance, instance_id, args.config)
        state = instance["State"]["Name"]
        if state != previous:
            print(f"Instance state: {state}", flush=True)
            previous = state
        if state == desired and (desired != "running" or (instance.get("PublicIpAddress") or instance.get("PrivateIpAddress"))):
            return instance
        require(state not in ("terminated", "shutting-down"), "Instance is being terminated.")
        time.sleep(10)
    raise RuntimeError(f"Timed out waiting for {desired}; inspect status before retrying.")


def update_cidr(args: argparse.Namespace, context: dict, cidr: str) -> None:
    if context["cidr"] == cidr:
        print(f"Ingress already matches {cidr}.")
        return
    request = {"StackName": context["stack"]["StackId"], "UsePreviousTemplate": True,
               "Capabilities": context["stack"].get("Capabilities", ["CAPABILITY_IAM"]),
               "Parameters": [{"ParameterKey": p["ParameterKey"], **(
                   {"ParameterValue": cidr} if p["ParameterKey"] == context["cidr_key"]
                   else {"UsePreviousValue": True})} for p in context["stack"]["Parameters"]]}
    print(f"{'Updating' if args.apply else 'Would update'} only {context['cidr_key']}: {context['cidr']} -> {cidr}.")
    if not args.apply:
        print(json.dumps(request, indent=2))
        return
    aws(args, "cloudformation", "update-stack", **request)
    deadline = time.monotonic() + 900
    previous = None
    while time.monotonic() < deadline:
        stack = aws(args, "cloudformation", "describe-stacks", StackName=context["stack"]["StackId"])["Stacks"][0]
        status = stack["StackStatus"]
        if status != previous:
            print(f"Stack status: {status}", flush=True)
            previous = status
        if status == "UPDATE_COMPLETE":
            refreshed = get_context(args)
            require(refreshed["stack"]["StackId"] == context["stack"]["StackId"]
                    and refreshed["instance"]["InstanceId"] == context["instance"]["InstanceId"],
                    "Stack or instance binding changed during the ingress update.")
            require(refreshed["cidr"] == cidr, "Updated security group does not match requested /32.")
            return
        require(status == "UPDATE_IN_PROGRESS" or status == "UPDATE_COMPLETE_CLEANUP_IN_PROGRESS",
                f"Unexpected stack update result: {status}; inspect stack events.")
        time.sleep(10)
    raise RuntimeError("Stack update timed out; inspect status before retrying.")


def restore_local_client(args: argparse.Namespace) -> None:
    require(args.config.get("_config_path"), "Choose client configuration explicitly with --config PATH or KIRO_DEMO_CONFIG.")
    client_config = Path(args.config["client"]["config_path"])
    ssh = args.config["ssh"]
    port = str(ssh["local_port"])
    require(client_config.is_file() and not client_config.is_symlink(), "Client config is missing or not a regular file.")
    original = client_config.read_bytes()
    config = json.loads(original)
    hosts = config.get("remoteHosts", {})
    require(isinstance(hosts, dict), "Unexpected remoteHosts structure.")
    remote = hosts.get(port)
    accepted_endpoints = (
        (ssh["gateway_alias"], "/usr/local/bin/kirocrew-demo"),
        (ssh["admin_alias"], "/usr/local/bin/kirocrew-owner-token"),
    )
    require(remote is None or (isinstance(remote, dict)
            and (remote.get("host"), remote.get("binPath")) in accepted_endpoints),
            f"Port {port} does not match an accepted demo host/wrapper pair; refusing removal.")
    config["runLocalGateway"] = True
    hosts.pop(port, None)
    config["remoteHosts"] = hosts
    print(f"Restore runLocalGateway=true and remove only remoteHosts[{port}]; preserve all other config keys.")
    if args.apply:
        pattern = args.config["client"].get("process_pattern")
        require(pattern and pattern.startswith("^"), "Configure an anchored client.process_pattern before applying rollback.")
        running = run(["pgrep", "-f", pattern])
        require(running.returncode == 1, "Quit the configured KiroCrew client before editing its persisted configuration.")
        tunnel(args, False, apply=True)
        backup = atomic_backup_write(client_config, original, (json.dumps(config, indent=2) + "\n").encode())
        print(f"Config restored; backup: {backup or 'unchanged'}. Reopen your KiroCrew client.")
    else:
        tunnel(args, False, apply=False)
        print("Would back up and atomically update client config after the configured KiroCrew client is quit.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["status", "start", "stop", "update-my-ip", "cleanup-plan", "local-client-rollback"])
    changes = parser.add_mutually_exclusive_group()
    changes.add_argument("--apply", action="store_true", help="perform the selected reversible operation")
    changes.add_argument("--dry-run", action="store_true", help="show the plan only (default)")
    parser.add_argument("--offline", action="store_true", help="use saved receipts; no AWS or public-IP requests; cannot apply")
    parser.add_argument("--client-ip", help="single client IPv4 as seen by EC2; required for private routing, otherwise discover public egress")
    parser.add_argument("--config", help="machine configuration JSON; alternatively set KIRO_DEMO_CONFIG")
    parser.add_argument("--evidence-dir", help="offline receipt directory override; only valid with --offline")
    parser.add_argument("--profile", help="existing AWS CLI profile (credentials are never copied)")
    args = parser.parse_args()
    config_path = args.config
    args.config = load_config(config_path, require_target=args.action != "local-client-rollback")
    require(not args.evidence_dir or args.offline, "--evidence-dir is only valid with --offline.")
    if args.evidence_dir:
        args.evidence_dir = str(Path(args.evidence_dir).expanduser().resolve())
    require(not (args.apply and args.offline), "--offline cannot be combined with --apply.")
    require(not (args.apply and args.action in ("status", "cleanup-plan")), "This action is read-only; omit --apply.")
    if args.action == "local-client-rollback":
        restore_local_client(args)
        return 0
    require(shutil.which("aws") is not None or args.offline, "AWS CLI is required.")
    context = get_context(args)
    instance_id = context["instance"]["InstanceId"]
    state = context["instance"]["State"]["Name"]
    print(json.dumps({"source": "saved receipts; may be stale" if args.offline else "live AWS reads",
                      "mode": "apply" if args.apply else "read-only / dry-run", "stack": args.config["aws"]["stack_name"],
                      "region": args.config["aws"]["region"], "instance": instance_id, "state": state,
                      "instance_type": context["instance"]["InstanceType"],
                      "architecture": context["instance"]["Architecture"],
                      "public_ip": context["instance"].get("PublicIpAddress"),
                      "private_ip": context["instance"].get("PrivateIpAddress"),
                      "ssh_address_mode": args.config["ssh"]["address_mode"],
                      "ssh_ingress": context["cidr"], "bucket": context["outputs"]["DemoBucketName"]}, indent=2))
    if args.action == "status":
        return 0
    require(context["stack"]["StackStatus"] in ("CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"),
            "Stack is not in a stable state; inspect its events before operating.")
    if args.action == "cleanup-plan":
        print("Deletion is deliberately manual. First export needed workspace/SEL evidence and quit the client.")
        print(f"Then unload the local tunnel and delete stack {context['stack']['StackName']}; its EC2 root EBS is destroyed.")
        print(f"Retained bucket: {context['outputs']['DemoBucketName']}; inspect/archive its contents before explicit deletion.")
        print("See infrastructure/RUNBOOK.md for exact cleanup and local-client rollback commands.")
        return 0
    original_ssh = check_local_files(args)
    if args.action == "stop":
        require(state in ("running", "stopped", "stopping"), f"Cannot stop from {state}.")
        tunnel(args, False, apply=args.apply)
        if state == "running":
            print(f"{'Stopping' if args.apply else 'Would gracefully stop'} {instance_id}; EBS and S3 remain billable.")
            if args.apply:
                aws(args, "ec2", "stop-instances", InstanceIds=[instance_id])
        if args.apply and state != "stopped":
            wait_instance(args, "stopped", instance_id)
        return 0
    client_ip = current_client_ip(args, context)
    if args.action == "start":
        require(state in ("running", "stopped", "pending"), f"Cannot start from {state}.")
    if state == "running":
        instance_address(context["instance"], args.config)  # Reject incompatible address mode before changing ingress.
    # Refresh and verify access before booting a stopped host. Otherwise its old
    # client's /32 would remain authorized while CloudFormation applies the update.
    update_cidr(args, context, client_ip + "/32")
    if args.action == "start":
        if state == "stopped":
            print(f"{'Starting' if args.apply else 'Would start'} {instance_id}.")
            if args.apply:
                aws(args, "ec2", "start-instances", InstanceIds=[instance_id])
        if args.apply and state != "running":
            context["instance"] = wait_instance(args, "running", instance_id)
        if not args.apply and state != "running":
            print("Would discover the configured public/private IPv4 target, then update the shared SSH aliases and prepare the tunnel.")
    if context["instance"]["State"]["Name"] == "running":
        address = instance_address(context["instance"], args.config)
        replacement, previous = ssh_update_text(original_ssh, address, args.config)
        print(f"{'Set' if args.apply else 'Would set'} the shared SSH HostName: {previous} -> {address}; pinned host-key settings preserved.")
        if args.apply:
            backup = atomic_backup_write(Path(args.config["ssh"]["config_path"]), original_ssh.encode(), replacement.encode())
            if backup:
                print(f"SSH config backup: {backup}")
        tunnel(args, True, apply=args.apply)
        if args.apply:
            print("Tunnel step complete. Verify the remote gateway and backend separately as documented in RUNBOOK.md.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
