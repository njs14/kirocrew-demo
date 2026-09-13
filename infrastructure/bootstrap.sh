#!/usr/bin/env bash
# Ubuntu 24.04 amd64 bootstrap for the KiroCrew EC2 demo.
# This file is embedded byte-for-byte in ec2-demo.json UserData.
# It installs OS packages only. The reviewed Crew/backend/MCP artifacts are
# installed separately over the administrator's SSH connection.
set -euo pipefail
umask 022

if [[ $(id -u) -ne 0 ]]; then
  printf '%s\n' 'Run this bootstrap as root.' >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates curl iptables python3-venv python3-boto3 unzip

if ! id crew >/dev/null 2>&1; then
  useradd --system --user-group --create-home \
    --home-dir /home/crew --shell /bin/bash crew
fi
if ! id mcp-demo >/dev/null 2>&1; then
  useradd --system --user-group --create-home \
    --home-dir /var/lib/mcp-demo --shell /usr/sbin/nologin mcp-demo
fi
# These service accounts receive neither sudo membership nor a password.
usermod --lock crew
usermod --lock mcp-demo

install -d -o root -g root -m 0755 /opt/kirocrew-demo /etc/kirocrew
install -d -o crew -g crew -m 0700 /home/crew
install -d -o crew -g crew -m 0700 /var/lib/kirocrew
install -d -o crew -g crew -m 0700 /var/lib/kirocrew/workspace
install -d -o mcp-demo -g mcp-demo -m 0700 /var/lib/mcp-demo

# IMDS belongs to the MCP service and host administration, not the agent UID.
# IMDSv2/hop-limit settings alone do not isolate host processes from credentials.
cat > /usr/local/sbin/kirocrew-imds-guard <<'GUARD'
#!/usr/bin/env bash
set -euo pipefail
crew_uid=$(id -u crew)
if ! iptables -w -C OUTPUT -d 169.254.169.254/32 \
  -m owner --uid-owner "$crew_uid" -j REJECT \
  --reject-with icmp-admin-prohibited 2>/dev/null; then
  iptables -w -I OUTPUT 1 -d 169.254.169.254/32 \
    -m owner --uid-owner "$crew_uid" -j REJECT \
    --reject-with icmp-admin-prohibited
fi
if ! ip6tables -w -C OUTPUT -d fd00:ec2::254/128 \
  -m owner --uid-owner "$crew_uid" -j REJECT \
  --reject-with icmp6-adm-prohibited 2>/dev/null; then
  ip6tables -w -I OUTPUT 1 -d fd00:ec2::254/128 \
    -m owner --uid-owner "$crew_uid" -j REJECT \
    --reject-with icmp6-adm-prohibited
fi
GUARD
chown root:root /usr/local/sbin/kirocrew-imds-guard
chmod 0755 /usr/local/sbin/kirocrew-imds-guard

cat > /etc/systemd/system/kirocrew-imds-guard.service <<'UNIT'
[Unit]
Description=Block the KiroCrew service UID from EC2 instance metadata
After=local-fs.target
Before=kirocrew-demo.service kirocrew-mcp-demo.service

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/kirocrew-imds-guard
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
UNIT
chmod 0644 /etc/systemd/system/kirocrew-imds-guard.service
systemctl daemon-reload
systemctl enable --now kirocrew-imds-guard.service

# Canonical Ubuntu EC2 AMIs normally include the official SSM Agent snap.
# If absent, use AWS's documented snap installation; no curl-pipe-shell.
if ! snap list amazon-ssm-agent >/dev/null 2>&1; then
  snap install amazon-ssm-agent --classic
fi
systemctl enable --now snap.amazon-ssm-agent.amazon-ssm-agent.service

# A marker is written only after package, firewall and SSM setup succeeds.
# CloudFormation CREATE_COMPLETE alone does not establish bootstrap success.
date -u '+%Y-%m-%dT%H:%M:%SZ' > /opt/kirocrew-demo/bootstrap-complete
chmod 0644 /opt/kirocrew-demo/bootstrap-complete
