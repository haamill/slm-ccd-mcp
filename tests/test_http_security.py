from conftest import TOKEN


async def test_missing_or_wrong_token(asgi_client):
    client,_=asgi_client
    assert (await client.post('/mcp',json={})).status_code==401
    assert (await client.get('/captures/no/no',headers={'Authorization':'Bearer wrong'})).status_code==401


async def test_invalid_host_or_origin(asgi_client):
    client,_=asgi_client
    assert (await client.post('/mcp',json={},headers={'Authorization':'Bearer '+TOKEN,'Host':'evil.example'})).status_code==403
    assert (await client.post('/mcp',json={},headers={'Authorization':'Bearer '+TOKEN,'Origin':'https://evil.example'})).status_code==403
