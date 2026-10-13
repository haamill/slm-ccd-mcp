import argparse
import asyncio
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import sys
import uuid
import numpy as np
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
import httpx2
from .config import load_config
from .controller import LabController
from .instance_lock import InstanceLock
from .devices.simulated import SimulatedSLM, SimulatedCamera
from .devices.hdslm import HDSLMOwner, probe_displays
from .devices.toupcam import ToupCamAdapter
from .devices.vendor import load_vendor_module, require_windows_x64
from .storage.assets import AssetStore
from .storage.captures import CaptureStore
from .storage.journal import OperationJournal
from .storage.common import write_json
from .imaging.io import read_codes


def build_controller(config):
    if config.mode=='hardware':
        require_windows_x64()
        for role,cfg in config.slms.items():
            if cfg.enabled and (not cfg.serial or cfg.desktop_xy is None):
                raise ValueError(f'{role} is unbound; run probe and set serial/desktop_xy first')
        slm=HDSLMOwner(config.slms,config.slm_sdk_dir)
        camera=ToupCamAdapter(config.camera,config.camera_sdk_root)
    else:
        slm=SimulatedSLM(config.slms); camera=SimulatedCamera(slm=slm)
    return LabController(config,slm,camera,AssetStore(config.runtime_dir,config.input_roots),
        CaptureStore(config.runtime_dir),OperationJournal(config.runtime_dir/'operations.sqlite'))


def probe(config):
    displays=probe_displays(config.slm_sdk_dir)
    handle=os.add_dll_directory(str(config.camera_sdk_root/'win/x64'))
    try:
        sdk=load_vendor_module('lab_probe_toupcam',config.camera_sdk_root/'python/toupcam.py')
        devices=sdk.Toupcam.EnumV2()
        cameras=[{'camera_id':d.id,'model':d.displayname,'mono':bool(d.model.flag & sdk.TOUPCAM_FLAG_MONO)} for d in devices]
    finally: handle.close()
    result={'displays':displays,'cameras':cameras,'device_opened':False,
        'note':'Enumeration only. Match physical SLM role before using hardware service.'}
    config.runtime_dir.mkdir(parents=True,exist_ok=True)
    write_json(config.runtime_dir/'probe.json',result)
    return result


async def run_smoke(url,token,*,http_client=None,allow_hardware=False,image_path=None,exposure_us=None):
    owned=http_client is None
    http=http_client or httpx2.AsyncClient(timeout=180.,trust_env=False)
    http.headers['Authorization']='Bearer '+token
    try:
        async with Client(streamable_http_client(url,http_client=http),read_timeout_seconds=180) as client:
            async def call(name,args):
                result=await client.call_tool(name,args)
                if result.is_error: raise RuntimeError(f'{name} failed: '+str(result.structured_content or result.content))
                return result
            status=(await call('lab_status',{})).structured_content
            hardware=status['mode']=='hardware'
            if hardware and (not allow_hardware or image_path is None or exposure_us is None):
                raise ValueError('Hardware smoke requires --allow-hardware, --image and --exposure-us')
            codes=read_codes(image_path) if hardware else np.zeros((1000,1000),dtype=np.uint16)
            buffer=io.BytesIO(); np.save(buffer,codes,allow_pickle=False); blob=buffer.getvalue()
            await call('lab_connect',{'roles':['slm2','ccd']})
            upload=(await call('asset_upload_begin',{'filename':'smoke.npy','total_bytes':len(blob),
                'sha256':hashlib.sha256(blob).hexdigest()})).structured_content
            ident=upload['upload_id']
            for offset in range(0,len(blob),1048576):
                await call('asset_upload_chunk',{'upload_id':ident,'offset':offset,
                    'data_base64':base64.b64encode(blob[offset:offset+1048576]).decode()})
            asset=(await call('asset_upload_finish',{'upload_id':ident})).structured_content
            request={'role':'slm2','source':'asset:'+asset['asset_id'],'bit_depth':8 if codes.dtype==np.uint8 else 10,
                'as_restore':True}
            loaded=(await call('slm_load_image',{'request':request})).structured_content['result']
            if not hardware:
                await call('slm_set_grating',{'fx':.01,'fy':0.})
            await call('ccd_set_settings',{'settings':{'exposure_us':exposure_us or 6000}})
            capture=(await call('ccd_capture',{'request':{'frames':1}})).structured_content['result']
            base=url.rstrip('/').removesuffix('/mcp')
            download=await http.get(base+'/captures/'+capture['capture_id']+'/raw_000.npy')
            download.raise_for_status()
            sha=hashlib.sha256(download.content).hexdigest()
            if sha!=capture['files']['raw_000.npy']['sha256']: raise ValueError('RAW download SHA256 mismatch')
            await call('slm_restore',{'role':'slm2'})
            return {'mode':status['mode'],'tools_count':len((await client.list_tools()).tools),
                'placement_xy':loaded['placement_xy'],'capture_id':capture['capture_id'],
                'raw_sha256':sha,'raw_sha256_matches':True,'preview':capture.get('preview')}
    finally:
        if owned: await http.aclose()


def main(argv=None):
    parser=argparse.ArgumentParser(prog='lab-mcp')
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('serve','probe'):
        cmd=commands.add_parser(name)
        cmd.add_argument('--config',type=Path,required=True)
        if name=='serve': cmd.add_argument('--mode',choices=('simulate','hardware'))
    init=commands.add_parser('init-token'); init.add_argument('--output',type=Path,default=Path('config/local.token'))
    smoke=commands.add_parser('smoke'); smoke.add_argument('--url',required=True)
    smoke.add_argument('--token-env',default='LAB_MCP_TOKEN'); smoke.add_argument('--allow-hardware',action='store_true')
    smoke.add_argument('--image',type=Path); smoke.add_argument('--exposure-us',type=int)
    args=parser.parse_args(argv)
    try:
        if args.command=='init-token':
            args.output.parent.mkdir(parents=True,exist_ok=True)
            with args.output.open('x',encoding='utf-8') as stream: stream.write(secrets.token_urlsafe(32)+'\n')
            print('Token saved to '+str(args.output.resolve())+'; value not printed.')
            return 0
        if args.command=='smoke':
            token=os.environ.get(args.token_env,'')
            if not token: raise ValueError('Token environment variable is not set')
            result=asyncio.run(run_smoke(args.url,token,allow_hardware=args.allow_hardware,
                image_path=args.image,exposure_us=args.exposure_us))
            print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
        cfg=load_config(args.config,mode=getattr(args,'mode',None))
        with InstanceLock(cfg.runtime_dir):
            if args.command=='probe': print(json.dumps(probe(cfg),ensure_ascii=False,indent=2)); return 0
            token=os.environ.get(cfg.token_env,'')
            if len(token)<16: raise ValueError('Set the configured token environment variable before serving')
            controller=build_controller(cfg)
            from .server.app import create_app
            import uvicorn
            app=create_app(cfg,controller,token=token)
            print(f'{cfg.mode} MCP endpoint: {cfg.public_base_url}/mcp',flush=True)
            uvicorn.run(app,host=cfg.host,port=cfg.port,workers=1,log_level='warning',timeout_graceful_shutdown=180)
        return 0
    except Exception as exc:
        message=str(exc)
        for key,value in os.environ.items():
            if 'TOKEN' in key and len(value)>=8: message=message.replace(value,'[redacted]')
        print('lab-mcp: '+message,file=sys.stderr)
        return 1
