import pytest
import asyncio
import httpx2
from test_controller import make_controller

TOKEN='test-only-secret-0123456789abcdef'


@pytest.fixture
async def asgi_client(tmp_path):
    from lab_mcp.server.app import create_app
    controller=make_controller(tmp_path)
    app=create_app(controller.config,controller,token=TOKEN)
    ready=asyncio.Event(); stop=asyncio.Event()
    async def own_lifespan():
        async with app.router.lifespan_context(app):
            ready.set()
            await stop.wait()
    task=asyncio.create_task(own_lifespan())
    await ready.wait()
    try:
        async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app),base_url='http://127.0.0.1:8765',trust_env=False) as client:
            yield client,controller
    finally:
        stop.set()
        await task
