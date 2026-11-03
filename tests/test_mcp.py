import json,os,sys,socket,subprocess,time
from pathlib import Path
import anyio
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

ROOT=Path(__file__).resolve().parents[1]
async def exercise(read,write):
    async with ClientSession(read,write) as client:
        await client.initialize()
        assert len((await client.list_tools()).tools)==9
        result=await client.call_tool('run_simulation',{'order_count':8,'fleet_size':3})
        assert not result.isError
        data=result.structuredContent or json.loads(result.content[0].text)
        frame=await client.call_tool('get_frame',{'run_id':data['id'],'tick':0})
        assert not frame.isError
        invalid=await client.call_tool('run_simulation',{'fleet_size':99})
        assert invalid.isError
        wrong=await client.call_tool('get_frame',{'run_id':data['id'],'tick':99999})
        assert wrong.isError

def test_real_stdio_mcp_server():
    async def run():
        with anyio.fail_after(30):
            async with stdio_client(StdioServerParameters(command=sys.executable,args=[str(ROOT/'mcp_server.py')],env=dict(os.environ))) as (read,write):await exercise(read,write)
    anyio.run(run,backend='asyncio')

def test_real_http_mcp_server():
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    process=subprocess.Popen([sys.executable,str(ROOT/'mcp_server.py'),'--http','--port',str(port)],env=dict(os.environ),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            assert process.poll() is None
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.1):break
            except OSError:time.sleep(.05)
        else:raise AssertionError('MCP server startup timeout')
        async def run():
            with anyio.fail_after(30):
                async with streamable_http_client(f'http://127.0.0.1:{port}/mcp') as(read,write,_):await exercise(read,write)
        anyio.run(run,backend='asyncio')
    finally:
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
