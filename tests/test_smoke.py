from conftest import TOKEN
from lab_mcp.cli import run_smoke


async def test_smoke_uses_real_mcp(asgi_client):
    http,_=asgi_client
    result=await run_smoke('http://127.0.0.1:8765/mcp',TOKEN,http_client=http)
    assert result['mode']=='simulate'
    assert result['placement_xy']==[470,161]
    assert result['raw_sha256_matches']
    assert result['tools_count']>=18
