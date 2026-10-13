from pathlib import Path
import re
import threading
import time
import uuid
import os
import numpy as np
from ..imaging.io import read_codes, read_phase_lut, checked_codes
from .common import checked_id, write_json, read_json, file_hash, confined_path


class AssetStore:
    def __init__(self,runtime_dir,input_roots):
        self.root=Path(runtime_dir).resolve()/'assets'
        self.pending=self.root/'uploads'
        self.pending.mkdir(parents=True,exist_ok=True)
        self.root=self.root.resolve(strict=True); self.pending=self.pending.resolve(strict=True)
        self.input_roots=[Path(p).resolve() for p in input_roots]
        self.lock=threading.RLock()

    def begin(self,filename,total_bytes,sha256):
        if type(total_bytes) is not int or not 0<total_bytes<=33554432:
            raise ValueError('Upload must contain 1..33554432 bytes')
        suffix=Path(filename).suffix.lower()
        if suffix not in ('.npy','.png','.bmp') or not re.fullmatch('[0-9a-f]{64}',sha256):
            raise ValueError('Invalid extension or SHA256')
        with self.lock:
            self.expire_uploads()
            ident=str(uuid.uuid4())
            meta={'upload_id':ident,'filename':Path(filename).name,'suffix':suffix,
                'total_bytes':total_bytes,'sha256':sha256,'created':time.time()}
            (self.pending/(ident+suffix)).touch(exist_ok=False)
            write_json(self.pending/(ident+'.json'),meta)
            return meta

    def chunk(self,upload_id,offset,data):
        checked_id(upload_id)
        if type(offset) is not int or offset<0 or not isinstance(data,bytes) or not 0<len(data)<=1048576:
            raise ValueError('Invalid chunk offset or size')
        with self.lock:
            meta=read_json(confined_path(self.pending,self.pending/(upload_id+'.json'),strict=True))
            path=confined_path(self.pending,self.pending/(upload_id+meta['suffix']),strict=True)
            size=path.stat().st_size
            if offset+len(data)>meta['total_bytes']:
                raise ValueError('Chunk exceeds declared upload')
            with path.open('r+b') as stream:
                if offset<size:
                    stream.seek(offset)
                    if stream.read(len(data))!=data:
                        raise ValueError('Conflicting repeated chunk')
                elif offset==size:
                    stream.seek(offset); stream.write(data); stream.flush()
                else:
                    raise ValueError('Chunks must be contiguous')
            return {'upload_id':upload_id,'received_bytes':path.stat().st_size}

    def finish(self,upload_id,*,packed_rgb=False,kind='codes'):
        checked_id(upload_id)
        with self.lock:
            existing=confined_path(self.root,self.root/(upload_id+'.json'))
            if existing.exists():
                return read_json(existing)
            meta=read_json(confined_path(self.pending,self.pending/(upload_id+'.json'),strict=True))
            source=confined_path(self.pending,self.pending/(upload_id+meta['suffix']),strict=True)
            if source.stat().st_size!=meta['total_bytes'] or file_hash(source)!=meta['sha256']:
                raise ValueError('Upload length or SHA256 mismatch')
            if kind=='codes': array=read_codes(source,packed_rgb=packed_rgb)
            elif kind=='phase_lut': array=read_phase_lut(source)
            else: raise ValueError('Unknown asset kind')
            result={**meta,'asset_id':upload_id,'kind':kind,'shape':list(array.shape),
                'dtype':str(array.dtype),'packed_rgb':packed_rgb}
            os.replace(source,confined_path(self.root,self.root/source.name))
            write_json(existing,result)
            (self.pending/(upload_id+'.json')).unlink()
            return result

    def resolve(self,source):
        if source.startswith('asset:'):
            ident=checked_id(source[6:])
            meta_path=confined_path(self.root,self.root/(ident+'.json'))
            if not meta_path.exists(): raise ValueError('Asset is not published')
            meta=read_json(meta_path)
            return confined_path(self.root,self.root/(ident+meta['suffix']),strict=True)
        path=Path(source).resolve(strict=True)
        if not any(path.is_relative_to(root) for root in self.input_roots):
            raise ValueError('Input path is outside allowed roots')
        if not path.is_file(): raise ValueError('Input must be a file')
        return path

    def list(self):
        return [read_json(confined_path(self.root,p,strict=True)) for p in sorted(self.root.glob('*.json'))]

    def register_codes(self,codes,label):
        array=checked_codes(codes)
        ident=str(uuid.uuid4()); path=confined_path(self.root,self.root/(ident+'.npy'))
        np.save(path,array,allow_pickle=False)
        meta={'asset_id':ident,'filename':label,'suffix':'.npy','sha256':file_hash(path),
            'total_bytes':path.stat().st_size,'kind':'codes','shape':list(array.shape),
            'dtype':str(array.dtype),'packed_rgb':False,'created':time.time()}
        write_json(confined_path(self.root,self.root/(ident+'.json')),meta)
        return meta

    def expire_uploads(self,max_age_s=3600):
        removed=0
        for path in self.pending.glob('*.json'):
            meta=read_json(confined_path(self.pending,path,strict=True))
            if time.time()-meta['created']>max_age_s:
                ident=checked_id(meta['upload_id'])
                suffix=meta['suffix']
                if suffix not in ('.npy','.png','.bmp'): continue
                target=confined_path(self.pending,self.pending/(ident+suffix))
                target.unlink(missing_ok=True); path.unlink(); removed+=1
        return {'removed':removed}
