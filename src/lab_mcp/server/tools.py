import asyncio
import base64
import json
from typing import Literal, Any
from pydantic import StrictInt
from mcp.server import MCPServer
from mcp.types import CallToolResult, TextContent, ImageContent, ToolAnnotations
from ..models import LoadRequest, CameraPatch, CaptureRequest, JointRequest, Role, SLMRole, Finite


def create_mcp(controller,assets,captures):
    mcp=MCPServer('SLM-CCD Lab',version='0.1.0',log_level='WARNING',instructions=(
        'Control only configured lab roles. Read lab_status first. Coordinates are pixels, '
        'exposure is microseconds. Simulation is not experimental evidence. Do not add a carrier '
        'to an image unless requested. Reuse operation_id to recover an uncertain network response.'))
    read=ToolAnnotations(readOnlyHint=True,destructiveHint=False,idempotentHint=True,openWorldHint=False)
    write=ToolAnnotations(readOnlyHint=False,destructiveHint=False,idempotentHint=False,openWorldHint=False)

    async def execute(op,args,operation_id=None,expected_version=None):
        result=await asyncio.to_thread(controller.execute,op,args,operation_id=operation_id,expected_version=expected_version)
        payload=result.get('result',{})
        if isinstance(payload,dict) and 'capture_id' in payload:
            payload['download_urls']={name:controller.config.public_base_url.rstrip('/')+'/captures/'+payload['capture_id']+'/'+name for name in payload['files']}
        content=[TextContent(type='text',text=json.dumps(result,ensure_ascii=False,allow_nan=False))]
        if isinstance(payload,dict) and 'capture_id' in payload and 'preview.png' in payload.get('files',{}):
            png=captures.registered_file(payload['capture_id'],'preview.png').read_bytes()
            content.append(ImageContent(type='image',data=base64.b64encode(png).decode('ascii'),mimeType='image/png'))
        return CallToolResult(content=content,structuredContent=result,isError=result['status']=='failed')

    @mcp.tool(annotations=read,structured_output=True)
    def lab_status()->dict[str,Any]:
        """Read cached role, image, CCD and state-version information without re-enumeration."""
        return controller.status()

    @mcp.tool(annotations=write,structured_output=False)
    async def lab_connect(roles:list[Role]|None=None,operation_id:str|None=None,expected_version:StrictInt|None=None)->CallToolResult:
        """Connect configured roles. SLM1 may be unavailable independently of SLM2 and CCD."""
        return await execute('lab_connect',{'roles':roles},operation_id,expected_version)

    @mcp.tool(annotations=write,structured_output=False)
    async def lab_disconnect(roles:list[Role]|None=None,operation_id:str|None=None,expected_version:StrictInt|None=None)->CallToolResult:
        """Release selected devices and try registered restoration; omit roles for all."""
        return await execute('lab_disconnect',{'roles':roles},operation_id,expected_version)

    @mcp.tool(annotations=read,structured_output=True)
    def asset_list()->list[dict[str,Any]]:
        """List published input assets. No arbitrary filesystem traversal."""
        return assets.list()

    @mcp.tool(annotations=write,structured_output=True)
    def asset_upload_begin(filename:str,total_bytes:StrictInt,sha256:str)->dict[str,Any]:
        """Begin an immutable upload of NPY/PNG/BMP, at most32MiB; provide exact SHA256."""
        return assets.begin(filename,total_bytes,sha256)

    @mcp.tool(annotations=write,structured_output=True)
    def asset_upload_chunk(upload_id:str,offset:StrictInt,data_base64:str)->dict[str,Any]:
        """Upload a contiguous base64 block, at most1MiB after decoding. Exact repeats accepted."""
        if len(data_base64)>1398140: raise ValueError('Encoded chunk exceeds limit')
        return assets.chunk(upload_id,offset,base64.b64decode(data_base64,validate=True))

    @mcp.tool(annotations=write,structured_output=True)
    def asset_upload_finish(upload_id:str,packed_rgb:bool=False,kind:Literal['codes','phase_lut']='codes')->dict[str,Any]:
        """Validate length/hash/data and publish asset ID. RGB10 packing must be explicit."""
        return assets.finish(upload_id,packed_rgb=packed_rgb,kind=kind)

    @mcp.tool(annotations=write,structured_output=False)
    async def slm_load_image(request:LoadRequest,operation_id:str|None=None,expected_version:StrictInt|None=None)->CallToolResult:
        """Load exact code image. Centered SLM2 default offset is(+10,+61); panel has no offset."""
        return await execute('slm_load_image',request.model_dump(mode='json'),operation_id,expected_version)

    @mcp.tool(annotations=write,structured_output=False)
    async def slm_set_offset(role:SLMRole,offset_x_px:StrictInt,offset_y_px:StrictInt,operation_id:str|None=None,expected_version:StrictInt|None=None)->CallToolResult:
        """Reposition current small image relative to panel center; never crop or accumulate offsets."""
        return await execute('slm_set_offset',{'role':role,'offset_x_px':offset_x_px,'offset_y_px':offset_y_px},operation_id,expected_version)

    @mcp.tool(annotations=write,structured_output=False)
    async def slm_set_grating(fx:Finite=0.,fy:Finite=0.,phi0:Finite=0.,mode:Literal['code','lut']='code',lut_source:str|None=None,operation_id:str|None=None,expected_version:StrictInt|None=None)->CallToolResult:
        """Set absolute SLM2 phase carrier in cycle/pixel. LUT mode needs explicit code→phase LUT."""
        return await execute('slm_set_grating',{'fx':fx,'fy':fy,'phi0':phi0,'mode':mode,'lut_source':lut_source},operation_id,expected_version)

    @mcp.tool(annotations=write,structured_output=False)
    async def slm_make_amplitude_grating(width:StrictInt,height:StrictInt,fx:Finite,fy:Finite,style:Literal['binary','sinusoidal']='binary',low:StrictInt=0,high:StrictInt=255,duty:Finite=.5,operation_id:str|None=None)->CallToolResult:
        """Create standalone8bit amplitude grating asset without changing a display."""
        return await execute('slm_make_amplitude_grating',{'width':width,'height':height,'fx':fx,'fy':fy,'style':style,'low':low,'high':high,'duty':duty},operation_id)

    @mcp.tool(annotations=write,structured_output=False)
    async def slm_show_uniform(role:SLMRole,gray:StrictInt,bit_depth:Literal[8,10]=10,operation_id:str|None=None,expected_version:StrictInt|None=None)->CallToolResult:
        """Show a full-panel uniform code; this does not promise optical extinction."""
        return await execute('slm_show_uniform',{'role':role,'gray':gray,'bit_depth':bit_depth},operation_id,expected_version)

    @mcp.tool(annotations=write,structured_output=False)
    async def slm_restore(role:SLMRole,operation_id:str|None=None,expected_version:StrictInt|None=None)->CallToolResult:
        """Show explicitly registered restoration image and placement/grating snapshot."""
        return await execute('slm_restore',{'role':role},operation_id,expected_version)

    @mcp.tool(annotations=read,structured_output=True)
    def ccd_get_settings()->dict[str,Any]:
        """Read CCD exposure in microseconds, SDK gain percent, ranges and effective RAW depth."""
        with controller.operation_lock: return controller.camera.settings()

    @mcp.tool(annotations=write,structured_output=False)
    async def ccd_set_settings(settings:CameraPatch,operation_id:str|None=None,expected_version:StrictInt|None=None)->CallToolResult:
        """Set and verify exposure/gain/AE. Explicit exposure defaults to auto-exposure off."""
        return await execute('ccd_set_settings',settings.model_dump(mode='json',exclude_none=True),operation_id,expected_version)

    @mcp.tool(annotations=write,structured_output=False)
    async def ccd_capture(request:CaptureRequest|None=None,operation_id:str|None=None,expected_version:StrictInt|None=None)->CallToolResult:
        """Capture1..16 fresh RAW frames with software settling/discard policy; return preview and downloads."""
        return await execute('ccd_capture',(request or CaptureRequest()).model_dump(mode='json'),operation_id,expected_version)

    @mcp.tool(annotations=write,structured_output=False)
    async def lab_load_and_capture(request:JointRequest,operation_id:str|None=None,expected_version:StrictInt|None=None)->CallToolResult:
        """Precheck all inputs, update CCD, thenSLM2/SLM1, settle and save fresh RAW without interleaving."""
        return await execute('lab_load_and_capture',request.model_dump(mode='json'),operation_id,expected_version)

    @mcp.tool(annotations=read,structured_output=True)
    def operation_get(operation_id:str)->dict[str,Any]:
        """Recover stored result byUUID; uncertain operations are never automatically replayed."""
        return controller.operation_get(operation_id)

    @mcp.resource('lab://status',mime_type='application/json')
    def status_resource()->str: return json.dumps(controller.status())

    @mcp.resource('capture://{capture_id}/metadata',mime_type='application/json')
    def capture_metadata(capture_id:str)->str: return captures.registered_file(capture_id,'manifest.json').read_text(encoding='utf-8')

    @mcp.resource('capture://{capture_id}/preview',mime_type='image/png')
    def capture_preview(capture_id:str)->bytes: return captures.registered_file(capture_id,'preview.png').read_bytes()
    return mcp
