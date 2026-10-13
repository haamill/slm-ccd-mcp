from conftest import TOKEN


async def test_download_requires_registered_id(asgi_client):
    client,_=asgi_client
    response=await client.get('/captures/not-a-uuid/secret',headers={'Authorization':'Bearer '+TOKEN})
    assert response.status_code==404
