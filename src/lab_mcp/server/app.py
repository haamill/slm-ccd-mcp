import asyncio
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route, Mount
from starlette.middleware import Middleware
from mcp.server.transport_security import TransportSecuritySettings
from .security import BearerAndOriginMiddleware
from .tools import create_mcp


def create_app(config,controller,*,token):
    mcp=create_mcp(controller,controller.assets,controller.captures)
    security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
        allowed_hosts=config.allowed_hosts,allowed_origins=config.allowed_origins)
    sdk_app=mcp.streamable_http_app(json_response=True,stateless_http=True,transport_security=security,host=config.host)

    async def download(request):
        try: path=controller.captures.registered_file(request.path_params['capture_id'],request.path_params['file_id'])
        except (ValueError, OSError): return JSONResponse({'error':'unknown capture file'},status_code=404)
        return FileResponse(path,filename=path.name)

    @asynccontextmanager
    async def lifespan(app):
        try:
            async with sdk_app.router.lifespan_context(sdk_app): yield
        finally: await asyncio.to_thread(controller.close)

    return Starlette(routes=[Route('/captures/{capture_id}/{file_id}',download),Mount('/',app=sdk_app)],
        lifespan=lifespan,middleware=[Middleware(BearerAndOriginMiddleware,token=token,
            allowed_hosts=config.allowed_hosts,allowed_origins=config.allowed_origins)])
