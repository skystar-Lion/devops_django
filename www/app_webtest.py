#/usr/bin/env python3

import asyncio
from aiohttp import web



async def hello(request):
    await asyncio.sleep(0.5)
    print(request)
    return web.Response(body="hello,world")

async def index(request):
    await asyncio.sleep(0.5)
    print(request.match_info)
    text= 'index %s' % request.match_info['name']
    return web.Response(body=text.encode('utf-8'))


async def init(loop):
    app = web.Application()
    app.add_routes([web.get('/', hello)])
    app.add_routes([web.get('/index/{name}', index)])
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', '8888')
    print('server start at http://127.0.0.1:8888/')
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()