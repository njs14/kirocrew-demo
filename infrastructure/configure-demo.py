#!/usr/bin/env python3
"""Provision only the dedicated EC2 demo config. Never prints generated tokens."""
import json
import os
import pwd
import secrets
from pathlib import Path

if os.geteuid() != 0:
    raise SystemExit('Run as root on the demo EC2 instance')
crew = pwd.getpwnam('crew')
mcp = pwd.getpwnam('mcp-demo')
state = Path('/var/lib/kirocrew')
etc = Path('/etc/kirocrew-demo')
etc.mkdir(mode=0o755, exist_ok=True)
token_path = etc / 'mcp-token'
if token_path.exists():
    token = token_path.read_text().strip()
else:
    token = secrets.token_urlsafe(48)
    token_path.write_text(token + '\n')
os.chown(token_path, 0, mcp.pw_gid)
token_path.chmod(0o640)

def write_owned(path, value, uid=crew.pw_uid, gid=crew.pw_gid, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit(f'Refusing to overwrite existing configuration: {path}')
    path.write_text(json.dumps(value, indent=2) + '\n')
    os.chown(path, uid, gid)
    path.chmod(mode)

write_owned(state / 'config.json', {
    'agent': {'approval_mode': 'interactive', 'acp_backend': '',
              'default_agent': 'enforcement-demo', 'subagent_auto_max': 3},
    'agents': {'enforcement-demo': {'kiro_agent': 'enforcement-demo', 'workspace': 'default',
                                  'description': 'EC2 Crew, MCP and IAM enforcement'}},
    'default_agent': 'enforcement-demo',
    'workspaces': {'default': {'dir': '/srv/kirocrew-demo/workspace'}},
    'hooks': {'auto_deny_tools': ['@aws-enforcement/crew_denied'], 'auto_approve_tools': []},
    'session': {'pool_size': 0},
    'mcp_gateway': {'prewarm_count': 0},
    'memory': {'embedding_threads': 1, 'embedding_bulk_threads': 1},
    'dashboard': {'url': 'http://127.0.0.1:5476', 'restore_sessions': False},
    'tunnel': {'enabled': False},
})
agent_dir = Path('/home/crew/.kiro/agents')
agent_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
for folder in [agent_dir.parent, agent_dir]:
    os.chown(folder, crew.pw_uid, crew.pw_gid)
write_owned(agent_dir / 'enforcement-demo.json', {
    'name': 'enforcement-demo',
    'description': 'Four fixed MCP reads for the EC2 enforcement demonstration',
    'prompt': 'Perform only the exact requested demo tool call. After any denial, stop and report the denial. Do not retry, substitute another tool, or use another route.',
    'tools': ['@aws-enforcement'], 'allowedTools': [], 'includeMcpJson': False,
    'mcpServers': {'aws-enforcement': {'url': 'http://127.0.0.1:8001/mcp',
                   'headers': {'Authorization': 'Bearer ' + token}}},
})
workspace = Path('/srv/kirocrew-demo/workspace')
workspace.mkdir(parents=True, exist_ok=True)
os.chown(workspace, crew.pw_uid, crew.pw_gid)
workspace.chmod(0o700)
sentinel = workspace / 'EC2-WORKSPACE.txt'
sentinel.write_text('This workspace resides on the CloudFormation-managed EC2 instance.\n')
os.chown(sentinel, crew.pw_uid, crew.pw_gid)
sentinel.chmod(0o600)
print('Dedicated Crew config, agent and protected MCP service token prepared')
