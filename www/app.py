#!/usr/bin/env python3

import asyncio
import os
import json
import time
import logging
from datetime import datetime
from aiohttp import web
from jinja2 import Environment, FileSystemLoader

import orm
from coroweb import add_routes, add_static

logging.basicConfig(level=logging.INFO, filename='/home/skystar/devops/devops_django/www/access_log.info')


def init_jinja2(app, **kw):
    logging.info('init jinja2..')
    options = dict(
        autoescape=kw.get('autoescape', True),
        block_start_string=kw.get('block_start_string', '{%'),
        block_end_string=kw.get('block_end_string', '%}'),
        variable_start_string=kw.get('variable_start_string', '{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        auto_reload=kw.get('auto_reload', True)
    )

    path = kw.get('path', None)
    if path is None:
        path = '/home/skystar/devops/devops_django/www/template'
        logging.info('set jinja2 templates path: %s' % path)
        env = Environment(loader=FileSystemLoader(path), **options)
        filters = kw.get('filters', None)
        #print(filters)
        if filters is not None:
            for name, f in filters.items():
                env.filters[name] = f

        app['__templating__'] = env


async def logger_factory(app, handler):
    async def logger(request):
        logging.info('received request: %s %s' % (request.method, request.path))
        return (await handler(request))
    return logger


async def data_factory(app, handler):
    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json:%s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logging.info('request form:%s' % (request.__data__))
        return (await handler(request))
    return parse_data


async def response_factory(app, handler):
    async def response(request):
        logging.info('response handler:')
        r = await handler(request)
        print(r)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octest-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r,ensure_ascii=False, default=lambda o:o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                print(resp)
                return resp
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))

        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return (u'one minute ago')
    if delta < 3600:
        return (u'%s minute ago' % (delta // 60))
    if delta < 86400:
        return (u'%s hours ago' % (delta // 3600))
    if delta < 604800:
        return (u'%s days ago' % (delta // 86400))
    dt = datetime.fromtimestamp(t)
    return (u'%s year %s month %s day' % (dt.year, dt.month, dt.day))


async def init(loop):
    await orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='awesome', password='awe@s0me', db='awesome')
    app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
    #app = web.Application(loop=loop)
    init_jinja2(app, filters=dict(datetime=datetime_filter))

    add_routes(app, 'handlers')
    add_static(app)
    srv = await loop.create_server(app.make_handler(), '192.168.1.107', 8888)
    logging.info('server start at http://192.168.1.107:8888')

    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
