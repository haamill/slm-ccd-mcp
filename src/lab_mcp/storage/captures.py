from pathlib import Path
import os
import shutil
import uuid
import numpy as np
from ..imaging.preview import make_preview
from .common import checked_id, write_json, read_json, file_hash


class CaptureStore:
    def __init__(self,runtime_dir):
        self.root=Path(runtime_dir).resolve()/'captures'
        self.root.mkdir(parents=True,exist_ok=True)

    def prepare(self,request,sensor_wh,effective_bits):
        w,h=sensor_wh
        if request.roi_xywh:
            x,y,rw,rh=request.roi_xywh
            if x+rw>w or y+rh>h: raise ValueError('ROI exceeds sensor')
            w,h=rw,rh
        estimate=w*h*2*request.frames+8*1024*1024
        if shutil.disk_usage(self.root).free<estimate:
            raise OSError('Insufficient disk space for requested RAW frames')
        return CaptureWriter(self,request,effective_bits)

    def registered_file(self,capture_id,file_id):
        checked_id(capture_id)
        if Path(file_id).name!=file_id or '/' in file_id or '\\' in file_id:
            raise ValueError('Invalid file ID')
        directory=self.root/capture_id
        meta_path=directory/'manifest.json'
        if not meta_path.exists(): raise ValueError('Unknown capture')
        manifest=read_json(meta_path)
        if file_id!='manifest.json' and file_id not in manifest['files']:
            raise ValueError('File is not registered')
        path=(directory/file_id).resolve(strict=True)
        if not path.is_relative_to(directory.resolve()): raise ValueError('Invalid final file path')
        return path


class CaptureWriter:
    def __init__(self,store,request,bits):
        self.store,self.request,self.bits=store,request,bits
        self.ident=str(uuid.uuid4()); self.root=store.root/self.ident
        self.root.mkdir()
        self.result={'capture_id':self.ident,'status':'capturing','saved_frames':0,
            'effective_bits':bits,'frames':[],'files':{},'request':request.model_dump(mode='json')}
        write_json(self.root/'manifest.json',self.result)

    def write_frame(self,frame):
        a=np.asarray(frame.raw)
        if a.ndim!=2 or a.dtype!=np.uint16: raise ValueError('RAW must be 2D uint16')
        index=self.result['saved_frames']; name=f'raw_{index:03d}.npy'
        temporary=self.root/(name+'.part')
        with temporary.open('wb') as stream:
            np.save(stream,a,allow_pickle=False); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary,self.root/name)
        self.result['files'][name]={'sha256':file_hash(self.root/name),'bytes':(self.root/name).stat().st_size}
        self.result['frames'].append(frame.metadata)
        self.result['saved_frames']+=1
        write_json(self.root/'manifest.json',self.result)
        if index==0:
            png,meta=make_preview(a,self.bits,bounds=self.request.preview_bounds)
            (self.root/'preview.png').write_bytes(png)
            self.result['files']['preview.png']={'sha256':file_hash(self.root/'preview.png'),'bytes':len(png)}
            self.result['preview']=meta
            write_json(self.root/'manifest.json',self.result)

    def finish(self,metadata):
        if self.result['saved_frames']!=self.request.frames: raise ValueError('Capture frame count mismatch')
        self.result.update(status='captured',metadata=metadata)
        write_json(self.root/'manifest.json',self.result)
        return self.result

    def fail(self,error):
        self.result.update(status='partial',error=error)
        write_json(self.root/'manifest.json',self.result)
        return self.result
