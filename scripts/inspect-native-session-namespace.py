#!/usr/bin/env python3
"""Read the current CLI process view for one prepared public-canary session.

Uses a private pinned SSH tunnel for the normal KiroCrew owner cookie exchange.
No native request, approval, process environment, credential file or probe is read.
The result corroborates current namespace visibility, never a historical syscall.
"""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

from demo_config import load_config
import live_setup_app as bridge

MODULES = ('sandbox.py', 'session_allocation.py', 'dashboard/session_memory.py',
           'dashboard/handlers/sessions.py', 'dashboard/routes/system.py', 'acp/client.py')
MAX_FILE = 4_000_000

class ReadbackError(RuntimeError):
    pass

def require(value, message):
    if not value:
        raise ReadbackError(message)

def read_json(path):
    path=Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size < MAX_FILE, 'invalid_input_file')
    return json.loads(path.read_text())

def source_hashes(root):
    root=Path(root).resolve(strict=True)
    result={}
    for name in MODULES:
        path=root/name
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root)
                and path.stat().st_size < MAX_FILE, 'invalid_local_source')
        result[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result

def absolute_path(value):
    require(isinstance(value,str) and re.fullmatch(r'/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+',value)
            and not {'.','..'}.intersection(PurePosixPath(value).parts), 'invalid_absolute_path')
    return value

def snapshot_request(before, hashes, remote_source_root, now=None):
    require(before.get('kind') == 'native_host_take_snapshot' and before.get('read_only') is True
            and before.get('probe_packets_sent') is False, 'invalid_host_snapshot')
    now=now or datetime.now(timezone.utc)
    observed=datetime.fromisoformat(before['observed_at'].replace('Z','+00:00'))
    require(observed.tzinfo is not None and -30 <= (now-observed).total_seconds() <= 1800,
            'host_snapshot_not_fresh')
    gateway=before.get('gateway',{})
    keys=('MainPID','NRestarts','InvocationID','ExecMainStartTimestamp','ActiveState','User')
    require(all(isinstance(gateway.get(k),str) and gateway[k] for k in keys)
            and gateway['ActiveState']=='active' and gateway['User']=='crew'
            and gateway['MainPID'].isdigit() and int(gateway['MainPID'])>1, 'invalid_gateway_identity')
    uid=before.get('crew_uid')
    require(type(uid) is int and uid > 0, 'invalid_crew_uid')
    machine=before.get('machine_id_sha256','')
    require(re.fullmatch(r'[a-f0-9]{64}',machine), 'invalid_machine_binding')
    fixture=before.get('files',{}).get('sensitive_canary',{})
    target=absolute_path(fixture.get('path'))
    require(PurePosixPath(target).name=='kirocrew-demo-control-canary.txt'
            and PurePosixPath(target).parent.name=='.aws'
            and fixture.get('regular') is True and fixture.get('absent') is False
            and fixture.get('uid')==uid and fixture.get('links')==1
            and re.fullmatch(r'[a-f0-9]{64}',fixture.get('sha256','')), 'invalid_public_canary')
    require(set(hashes)==set(MODULES) and all(re.fullmatch(r'[a-f0-9]{64}',h) for h in hashes.values()),
            'invalid_source_hashes')
    return {'gateway_pid':int(gateway['MainPID']), 'gateway_identity':{k:gateway[k] for k in keys},
            'machine_id_sha256':machine,'crew_uid':uid,'canary':target,'source_hashes':hashes,
            'remote_source_root':absolute_path(remote_source_root)}

def select_binding(body, slot):
    require(re.fullmatch(r'chat-[A-Za-z0-9_-]{1,90}',slot), 'invalid_slot')
    require(isinstance(body,dict) and isinstance(body.get('sessions'),list), 'invalid_memory_response')
    key='dashboard:'+slot
    rows=[row for row in body['sessions'] if isinstance(row,dict) and (row.get('key')==key or row.get('slot_key')==slot)]
    require(len(rows)==1, 'runtime_binding_ambiguous')
    row=rows[0]
    require(row.get('key')==key and row.get('slot_key')==slot and row.get('agent')=='host-controls-demo'
            and row.get('owns_runtime') is True and type(row.get('pid')) is int and row['pid']>1,
            'unexpected_session_runtime')
    return {k:row.get(k) for k in ('key','slot_key','agent','pid','owns_runtime','prompts')}

def corroborates(remote):
    host=remote.get('host_canary',{})
    require(host.get('exists') is True and host.get('regular') is True and host.get('symlink') is False,
            'host_canary_unavailable')
    processes=remote.get('processes',[])
    require(0<len(processes)<=64, 'invalid_descendant_count')
    cli=[r for r in processes if r.get('exe_basename') in ('kiro-cli','kiro-cli-chat')]
    require(bool(cli), 'no_native_cli_descendants')
    return all(r.get('identity_stable_during_read') is True and r.get('mount_namespace_differs_from_gateway') is True
               and r.get('canary_in_process_root')=={'exists':False,'errno':2}
               and any(m.get('filesystem')=='tmpfs' for m in r.get('aws_mounts',[])) for r in cli)

REMOTE = r'''

import os, sys, json, stat, hashlib
from pathlib import Path
from datetime import datetime, timezone
request = json.loads(sys.stdin.readline())
def require(value, message):
    if not value: raise RuntimeError(message)
require(hashlib.sha256(Path('/etc/machine-id').read_bytes()).hexdigest() == request['machine_id_sha256'], 'machine_mismatch')
gateway = request['gateway_pid']
root = request['runtime_pid']
target = request['canary']
directory = str(Path(target).parent)
def identity(pid):
    proc = Path('/proc') / str(pid)
    raw = (proc/'stat').read_text()
    fields = raw[raw.rfind(')')+2:].split()
    return {'pid':pid, 'ppid':int(fields[1]), 'start_ticks':int(fields[19])}
def filemeta(path):
    try:
        st = os.lstat(path)
        return {'exists':True, 'regular':stat.S_ISREG(st.st_mode), 'directory':stat.S_ISDIR(st.st_mode),
                'symlink':stat.S_ISLNK(st.st_mode), 'uid':st.st_uid, 'gid':st.st_gid,
                'mode':stat.S_IMODE(st.st_mode), 'bytes':st.st_size, 'device':st.st_dev, 'inode':st.st_ino}
    except FileNotFoundError:
        return {'exists':False, 'errno':2}
    except OSError as error:
        return {'exists':None, 'errno':error.errno}
import subprocess
def service():
    output=subprocess.run(['systemctl','show','kirocrew-demo.service','--no-pager',
        *['--property='+key for key in request['gateway_identity']]],capture_output=True,check=True,timeout=5)
    actual=dict(line.split('=',1) for line in output.stdout.decode().splitlines() if '=' in line)
    require(actual == request['gateway_identity'], 'gateway_service_changed')
service()
gateway_before = identity(gateway)
runtime_before = identity(root)
require(runtime_before['ppid'] == gateway, 'runtime_not_gateway_child')
gateway_ns = os.readlink('/proc/%d/ns/mnt' % gateway)
rows, queue, seen = [], [root], set()
while queue:
    pid = queue.pop(0)
    if pid in seen: continue
    require(len(seen) < 64, 'descendant_bound')
    seen.add(pid)
    proc = Path('/proc') / str(pid)
    before = identity(pid)
    status = dict(line.split(':',1) for line in (proc/'status').read_text().splitlines() if ':' in line)
    uid = [int(value) for value in status['Uid'].split()]
    require(all(value == request['crew_uid'] for value in uid), 'descendant_uid_mismatch')
    exe = Path(os.readlink(proc/'exe')).name
    namespaces = {key:os.readlink(proc/'ns'/key) for key in ('mnt','user')}
    children = set()
    for task in (proc/'task').iterdir():
        children.update(int(value) for value in (task/'children').read_text().split())
    for child in sorted(children):
        if identity(child)['ppid'] == pid: queue.append(child)
    mounts=[]
    for line in (proc/'mountinfo').read_text().splitlines():
        fields=line.split()
        if len(fields)>6 and fields[4] == directory:
            split=fields.index('-')
            mounts.append({'mount_id':fields[0], 'parent_id':fields[1], 'device':fields[2],
                           'root':fields[3], 'mount_point':fields[4], 'options':fields[5],
                           'filesystem':fields[split+1], 'source':fields[split+2]})
    canary=filemeta(str(proc/'root')+target)
    masked_dir=filemeta(str(proc/'root')+directory)
    after=identity(pid)
    require(before == after, 'process_identity_changed')
    rows.append({**before, 'exe_basename':exe, 'uid':uid, 'gid':[int(value) for value in status['Gid'].split()],
                 'namespaces':namespaces, 'mount_namespace_differs_from_gateway':namespaces['mnt'] != gateway_ns,
                 'no_new_privs':int(status.get('NoNewPrivs','0').strip()), 'seccomp':int(status.get('Seccomp','0').strip()),
                 'aws_mounts':mounts, 'canary_in_process_root':canary, 'aws_directory_in_process_root':masked_dir,
                 'identity_stable_during_read':True})
require(identity(root) == runtime_before and identity(gateway) == gateway_before, 'runtime_changed')
service()
sources={}
source_root=Path(request['remote_source_root'])
for name, expected in request['source_hashes'].items():
    path=source_root/name
    for ancestor in (path,*path.parents):
        metadata=ancestor.lstat()
        require(not stat.S_ISLNK(metadata.st_mode) and metadata.st_uid == 0 and not metadata.st_mode & 0o022, 'source_ancestor_unprotected')
    st=path.lstat()
    require(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and not st.st_mode & 0o022,'source_ownership')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    require(digest == expected,'source_mismatch')
    sources[name]={'sha256':digest,'uid':st.st_uid,'mode':stat.S_IMODE(st.st_mode)}
print(json.dumps({'observed_at':datetime.now(timezone.utc).isoformat(), 'gateway':gateway_before,
 'gateway_mount_namespace':gateway_ns, 'runtime':runtime_before, 'processes':rows,
 'host_canary':filemeta(target), 'host_aws_directory':filemeta(directory), 'source_bindings':sources,
 'read_only':True, 'environment_read':False, 'public_canary_contents_read':False, 'namespace_entered':False,
 'process_launched_inside_target_namespace':False}))
'''

async def run(args):
    import aiohttp
    output=Path(args.output)
    require(not output.exists() and output.parent.is_dir(), 'output_must_be_fresh')
    before=read_json(args.before)
    request=snapshot_request(before,source_hashes(args.source_root),args.remote_source_root)
    # Validate the slot before any SSH authentication or process inspection.
    require(re.fullmatch(r'chat-[A-Za-z0-9_-]{1,90}',args.slot), 'invalid_slot')
    config=load_config(args.config,require_target=True)
    base=f"http://localhost:{config['ssh']['local_port']}"
    async with bridge.owned_tunnel(config) as socket:
        token=await asyncio.to_thread(bridge.owner_token,config)
        connector=aiohttp.UnixConnector(path=socket)
        async with aiohttp.ClientSession(connector=connector,cookie_jar=aiohttp.CookieJar(),trust_env=False,
                timeout=aiohttp.ClientTimeout(total=35),headers={'Origin':base}) as http:
            async with http.get(base+'/',params={'token':token},allow_redirects=False) as response:
                require(response.status in (200,302,303),'cookie_exchange_failed')
                await bridge._body(response)
            del token
            async def binding():
                async with http.get(base+'/api/sessions/memory',allow_redirects=False) as response:
                    require(response.status==200,'memory_read_failed')
                    body=json.loads(await bridge._body(response))
                return {'observed_at':datetime.now(timezone.utc).isoformat(),'row':select_binding(body,args.slot)}
            first=await binding()
            request['runtime_pid']=first['row']['pid']
            raw=await asyncio.to_thread(bridge._ssh,config,['sudo','-n','/usr/bin/python3','-I','-c',REMOTE],
                                      stdin=(json.dumps(request)+'\n').encode())
            remote=json.loads(raw)
            second=await binding()
            require(first['row']==second['row'],'session_binding_changed')
    matched=corroborates(remote)
    result={'schema_version':1,'kind':'exact_native_session_namespace_readback','slot':args.slot,
            'api_route':'/api/sessions/memory','api_binding_before':first,'api_binding_after':second,
            'host_snapshot_sha256':hashlib.sha256(Path(args.before).read_bytes()).hexdigest(),
            'inspector_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'remote':remote,
            'namespace_mask_corroborated_for_current_cli_descendants':matched,
            'limitations':['This binds current CLI descendants after the result, not the historical syscall PID.',
                           'A missing-path native result remains CLI argument validation, not a hook denial.']}
    with output.open('x') as stream:
        stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'output':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                      'namespace_mask_corroborated':matched}))
    return 0 if matched else 1

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ('config','slot','before','source-root','output'):
        parser.add_argument('--'+option,required=True)
    parser.add_argument('--remote-source-root',default='/opt/kirocrew/venv/lib/python3.12/site-packages/kiro_crew')
    args=parser.parse_args()
    try:
        return asyncio.run(run(args))
    except (ReadbackError,bridge.AppSetupError) as error:
        print(json.dumps({'failed':True,'reason':str(error)}));return 1
    except Exception as error:
        # Raw HTTP/SSH errors can contain product authentication or other sessions.
        print(json.dumps({'failed':True,'error_type':type(error).__name__}));return 1

if __name__=='__main__':
    raise SystemExit(main())
