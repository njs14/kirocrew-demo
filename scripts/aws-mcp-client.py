#!/usr/bin/env python3
"""Use the configured primary AWS MCP transport without exposing credentials."""
import asyncio,json,sys,tomllib,os
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
 c=tomllib.loads((Path.home()/'.codex/config.toml').read_text())['mcp_servers']['aws-mcp']
 if not c.get('enabled',True): raise SystemExit('aws-mcp is disabled')
 env=dict(os.environ); env.update(c.get('env',{}))
 params=StdioServerParameters(command=c['command'],args=c['args'],env=env)
 async with stdio_client(params) as (r,w):
  async with ClientSession(r,w,read_timeout_seconds=120) as s:
   init=await s.initialize()
   if len(sys.argv)==1:
    result=await s.list_tools()
    print(json.dumps({'server':init.model_dump(by_alias=True),'tools':[t.model_dump(by_alias=True) for t in result.tools]},indent=2))
   else:
    request=json.loads(Path(sys.argv[1]).read_text())
    result=await s.call_tool(request['name'],request.get('arguments',{}))
    print(result.model_dump_json(indent=2,by_alias=True))
asyncio.run(main())
