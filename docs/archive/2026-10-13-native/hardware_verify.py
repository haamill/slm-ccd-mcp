"""Site acceptance through the actual MCP transport; never print credentials or base64."""
import argparse
import asyncio
import hashlib
import io
import json
from pathlib import Path
import uuid
import base64
import numpy as np
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

ROOT=Path('D:/ExpSoftware/slm-ccd-mcp')
URL='http://10.195.186.75:8765'


async def main(role):
    token=(ROOT/'config/local.token').read_text(encoding='utf-8').strip()
    destination=ROOT/'runtime'/('hardware-dark-verification.json' if role=='ccd' else 'hardware-slm2-verification.json')
    report={'mode':'hardware','laser':'off, per user','roles':[role],'events':[],'status':'running'}
    def record(name,result):
        report['events'].append({'tool':name,'result':result})
        destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    async with httpx2.AsyncClient(timeout=180.,trust_env=False,headers={'Authorization':'Bearer '+token}) as http:
        async with Client(streamable_http_client(URL+'/mcp',http_client=http),read_timeout_seconds=180) as client:
            async def call(name,args,mutating=True):
                if mutating: args={**args,'operation_id':str(uuid.uuid4())}
                result=await client.call_tool(name,args)
                record(name,result.structured_content)
                if result.is_error: raise RuntimeError(name+': '+str(result.structured_content or result.content))
                return result.structured_content
            passed=False
            try:
                await call('lab_connect',{'roles':[role]})
                if role=='ccd':
                    settings=await call('ccd_get_settings',{},False)
                    report['original_settings_readback']=settings
                    # Same measured exposure; manual mode fixes it during this dark-frame acceptance.
                    await call('ccd_set_settings',{'settings':{'exposure_us':settings['exposure_us']}})
                    capture=(await call('ccd_capture',{'request':{'frames':1}}))['result']
                    digest=hashlib.sha256()
                    async with http.stream('GET',URL+'/captures/'+capture['capture_id']+'/raw_000.npy') as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_bytes(): digest.update(chunk)
                    report['raw_download_sha256_matches']=digest.hexdigest()==capture['files']['raw_000.npy']['sha256']
                    if not report['raw_download_sha256_matches']: raise RuntimeError('RAW download SHA mismatch')
                    report['capture_id']=capture['capture_id']; report['preview']=capture.get('preview')
                else:
                    # A clearly identified new small pattern, never represented as a recovered prior hologram.
                    yy,xx=np.indices((128,128)); codes=np.where((xx//16+yy//16)%2,768,256).astype(np.uint16)
                    local=ROOT/'assets'/'acceptance_slm2_128_native10.npy'; np.save(local,codes,allow_pickle=False)
                    buffer=io.BytesIO(); np.save(buffer,codes,allow_pickle=False); blob=buffer.getvalue()
                    begin=await call('asset_upload_begin',{'filename':local.name,'total_bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()},False)
                    await call('asset_upload_chunk',{'upload_id':begin['upload_id'],'offset':0,'data_base64':base64.b64encode(blob).decode()},False)
                    asset=await call('asset_upload_finish',{'upload_id':begin['upload_id']},False)
                    load=(await call('slm_load_image',{'request':{'role':'slm2','source':'asset:'+asset['asset_id'],'bit_depth':10,'as_restore':True}}))['result']
                    await call('slm_set_offset',{'role':'slm2','offset_x_px':11,'offset_y_px':61})
                    await call('slm_set_offset',{'role':'slm2','offset_x_px':10,'offset_y_px':61})
                    await call('slm_set_grating',{'fx':.01,'fy':0.})
                    restored=(await call('slm_restore',{'role':'slm2'}))['result']
                    report['restored_array_sha256_matches']=load['displayed_array_sha256']==restored['displayed_array_sha256']
                    if not report['restored_array_sha256_matches']: raise RuntimeError('Restore array hash mismatch')
                passed=True
            finally:
                await call('lab_disconnect',{'roles':[role]})
                report['after_disconnect']=await call('lab_status',{},False)
                report['status']='passed' if passed else 'failed'
                destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(destination),'role':role,'capture_id':report.get('capture_id'),
        'download_hash_matches':report.get('raw_download_sha256_matches'),'preview':report.get('preview')},ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('role',choices=['ccd','slm2'])
    asyncio.run(main(parser.parse_args().role))
