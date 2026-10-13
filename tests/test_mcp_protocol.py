import base64
import hashlib
import io
import asyncio
import threading
import uuid
import numpy as np
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from conftest import TOKEN


async def test_upload_load_capture_preview_download(asgi_client):
    http,controller=asgi_client; http.headers['Authorization']='Bearer '+TOKEN
    stream=io.BytesIO(); np.save(stream,np.zeros((1000,1000),dtype=np.uint16)); blob=stream.getvalue()
    async with Client(streamable_http_client('http://127.0.0.1:8765/mcp',http_client=http)) as client:
        tools=await client.list_tools()
        assert {'lab_status','slm_set_grating','ccd_capture','lab_load_and_capture','operation_get'}.issubset({t.name for t in tools.tools})
        begin=await client.call_tool('asset_upload_begin',{'filename':'x.npy','total_bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()})
        ident=begin.structured_content['upload_id']
        for offset in range(0,len(blob),1048576):
            result=await client.call_tool('asset_upload_chunk',{'upload_id':ident,'offset':offset,'data_base64':base64.b64encode(blob[offset:offset+1048576]).decode()})
            assert not result.is_error
        done=await client.call_tool('asset_upload_finish',{'upload_id':ident})
        asset=done.structured_content['asset_id']
        loaded=await client.call_tool('slm_load_image',{'request':{'role':'slm2','source':'asset:'+asset}})
        assert loaded.structured_content['result']['placement_xy']==[470,161]
        result=await client.call_tool('ccd_set_settings',{'settings':{'exposure_us':6000}})
        assert result.structured_content['result']['exposure_us']==6000
        captured=await client.call_tool('ccd_capture',{'request':{'settle_s':0.,'discard_frames':0}})
        assert not captured.is_error
        assert any(block.type=='image' for block in captured.content)
        capture=captured.structured_content['result']
        download=await http.get('/captures/'+capture['capture_id']+'/raw_000.npy')
        assert download.status_code==200
        assert hashlib.sha256(download.content).hexdigest()==capture['files']['raw_000.npy']['sha256']
        resource=await client.read_resource('capture://'+capture['capture_id']+'/metadata')
        assert resource.contents


async def test_legacy_handshake_client(asgi_client):
    http,_=asgi_client; http.headers['Authorization']='Bearer '+TOKEN
    async with Client(streamable_http_client('http://127.0.0.1:8765/mcp',http_client=http),mode='legacy') as client:
        assert (await client.call_tool('lab_status',{})).structured_content['mode']=='simulate'


async def test_logs_do_not_contain_token_or_base64(asgi_client,capsys):
    http,_=asgi_client; http.headers['Authorization']='Bearer '+TOKEN
    await http.get('/captures/not-valid/missing')
    output=capsys.readouterr()
    assert TOKEN not in output.out+output.err


async def test_cancelled_client_does_not_reexecute(asgi_client):
    http,controller=asgi_client; http.headers['Authorization']='Bearer '+TOKEN
    entered=threading.Event(); release=threading.Event(); calls=[]
    original=controller.camera.capture
    def delayed(*args):
        calls.append('capture'); entered.set(); release.wait(3); return original(*args)
    controller.camera.capture=delayed
    ident=str(uuid.uuid4())
    args={'request':{'settle_s':0.,'discard_frames':0},'operation_id':ident}
    async with Client(streamable_http_client('http://127.0.0.1:8765/mcp',http_client=http)) as client:
        pending=asyncio.create_task(client.call_tool('ccd_capture',args))
        assert await asyncio.to_thread(entered.wait,2)
        pending.cancel()
        try: await pending
        except asyncio.CancelledError: pass
        release.set()
        for _ in range(50):
            record=controller.operation_get(ident)
            if record['status']=='succeeded': break
            await asyncio.sleep(.02)
        assert record['status']=='succeeded'
        retried=await client.call_tool('ccd_capture',args)
        assert retried.structured_content['operation_id']==ident
        assert calls==['capture']
