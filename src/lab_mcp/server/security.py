import hmac
from starlette.responses import JSONResponse


class BearerAndOriginMiddleware:
    def __init__(self,app,*,token,allowed_hosts,allowed_origins):
        if len(token)<16 or '\n' in token or '\r' in token: raise ValueError('Use a nonempty strong token')
        self.app=app; self.expected=('Bearer '+token).encode('utf-8')
        self.hosts={h.lower() for h in allowed_hosts}; self.origins=set(allowed_origins)

    async def __call__(self,scope,receive,send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        headers=dict(scope['headers'])
        if not hmac.compare_digest(headers.get(b'authorization',b''),self.expected):
            return await JSONResponse({'error':'unauthorized'},status_code=401)(scope,receive,send)
        host=headers.get(b'host',b'').decode('latin1').lower()
        origin=headers.get(b'origin')
        if host not in self.hosts or (origin is not None and origin.decode('latin1') not in self.origins):
            return await JSONResponse({'error':'invalid host or origin'},status_code=403)(scope,receive,send)
        await self.app(scope,receive,send)
