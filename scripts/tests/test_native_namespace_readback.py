import copy
from datetime import datetime,timezone,timedelta
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
SCRIPTS=Path(__file__).resolve().parents[1];sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('namespace_readback',SCRIPTS/'inspect-native-session-namespace.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
NOW=datetime(2026,9,14,15,0,tzinfo=timezone.utc)

def snapshot():
 return {'kind':'native_host_take_snapshot','read_only':True,'probe_packets_sent':False,'observed_at':NOW.isoformat(),'crew_uid':999,'machine_id_sha256':'a'*64,'gateway':{'MainPID':'100','NRestarts':'0','InvocationID':'abc','ExecMainStartTimestamp':'today','ActiveState':'active','User':'crew'},'files':{'sensitive_canary':{'path':'/home/crew/.aws/kirocrew-demo-control-canary.txt','regular':True,'absent':False,'uid':999,'links':1,'sha256':'b'*64}}}
def row():
 return {'key':'dashboard:chat-1-123','slot_key':'chat-1-123','agent':'host-controls-demo','pid':200,'owns_runtime':True,'prompts':2}
def remote():
 return {'host_canary':{'exists':True,'regular':True,'symlink':False},'processes':[{'exe_basename':'kiro-cli-chat','identity_stable_during_read':True,'mount_namespace_differs_from_gateway':True,'canary_in_process_root':{'exists':False,'errno':2},'aws_mounts':[{'filesystem':'tmpfs'}]}]}
class NamespaceGuards(unittest.TestCase):
 def request(self,s):return m.snapshot_request(s,{n:'c'*64 for n in m.MODULES},'/opt/crew/kiro_crew',NOW)
 def test_derives_current_identity(self):
  r=self.request(snapshot());self.assertEqual(r['gateway_pid'],100);self.assertEqual(r['crew_uid'],999);self.assertEqual(r['canary'],'/home/crew/.aws/kirocrew-demo-control-canary.txt')
 def test_rejects_stale_and_future_snapshot(self):
  for seconds in (-1801,31):
   s=snapshot();s['observed_at']=(NOW+timedelta(seconds=seconds)).isoformat()
   with self.assertRaises(m.ReadbackError):self.request(s)
 def test_rejects_wrong_fixture_or_gateway(self):
  for edit in (lambda s:s['files']['sensitive_canary'].update(path='/home/crew/.aws/credentials'),lambda s:s['files']['sensitive_canary'].update(regular=False),lambda s:s['gateway'].update(User='root'),lambda s:s.update(crew_uid=0)):
   s=snapshot();edit(s)
   with self.assertRaises(m.ReadbackError):self.request(s)
 def test_exact_session_selected(self):
  other=row();other.update(key='dashboard:chat-2',slot_key='chat-2')
  self.assertEqual(m.select_binding({'sessions':[other,row()]},'chat-1-123'),row())
 def test_ambiguous_or_non_native_runtime_rejected(self):
  for rows in ([row(),row()],[],[{**row(),'agent':'other'}],[{**row(),'owns_runtime':False}],[{**row(),'pid':True}],[{**row(),'slot_key':'other'}]):
   with self.assertRaises(m.ReadbackError):m.select_binding({'sessions':rows},'chat-1-123')
 def test_current_mask_needs_tmpfs_and_missing_target(self):
  self.assertTrue(m.corroborates(remote()))
  for change in ({'aws_mounts':[{'filesystem':'ext4'}]},{'mount_namespace_differs_from_gateway':False},{'canary_in_process_root':{'exists':True}},{'identity_stable_during_read':False}):
   r=remote();r['processes'][0].update(change);self.assertFalse(m.corroborates(r))
 def test_requires_cli_and_host_fixture(self):
  for r in ({**remote(),'processes':[]},{**remote(),'host_canary':{'exists':False}}):
   with self.assertRaises(m.ReadbackError):m.corroborates(r)
 def test_local_sources_all_required_and_confined(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for name in m.MODULES:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('reviewed source')
   self.assertEqual(set(m.source_hashes(root)),set(m.MODULES))
   (root/m.MODULES[0]).unlink();(root/m.MODULES[0]).symlink_to(root/m.MODULES[1])
   with self.assertRaises(m.ReadbackError):m.source_hashes(root)
 def test_remote_program_parses(self):compile(m.REMOTE,'remote-readback','exec')
if __name__=='__main__':unittest.main()
