import logging; logging.basicConfig(level=logging.INFO)
import asyncio, time, json, os
import configparser
from datetime import datetime
from aiohttp import web
from jinja2 import Environment,FileSystemLoader
import www.orm
from www.coroweb import add_routes,add_static


def init_jinja2(app,**kw):
    logging.info('init jinja2...')
    config = configparser.ConfigParser()
    config.read('../conf/application.ini')
    option = dict(
        autoescape=config.getboolean('jinja2','autoe_space'),
        block_start_string=config.get('jinja2','block_start_string'),
        block_end_string=config.get('jinja2','block_end_string'),
        variable_start_string=config.get('jinja2','variable_start_string'),
        variable_end_string=config.get('jinja2','variable_end_string'),
        auto_reload=config.getboolean('jinja2','auto_reload')
    )
    path = config.get('jinja2', 'path')
    if path is None or path == '':
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template')
    logging.info('set jinja2 templates path %s' % path)
    env = Environment(loader=FileSystemLoader(path), **option)
    filter = kw.get('filter', None)
    if filter is not None:
        for name, f in filter.items():
            env.filters[name] = f
    app['__templating__'] = env


async def loggerFactory(app,handler):
    async def logger(request):
        logging.info('request:%s,%s' % (request.method, request.path))
        return await(handler(request))
    return logger


async def dataFactory(app,handler):
    async def parseData(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json:%s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = await  request.post()
                logging.info('request form:%s' % str(request.__data__))
            return (await handler(request))
    return parseData


async def responseFactory(app, handler):
    async def response(request):
        logging.info('response handler...')
        r = await handler(request)
        if isinstance(r, web.WebSocketResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[:9])
            resp = web.Response(body=r.encode('UTF-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r,ensure_ascii=False, default=lambda o: o.__dict__).encode('UTF-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and r > 100 and r < 600:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t,int) and r > 100 and r < 600:
                return web.Response(t, str(m))
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type='text/plain;charset=utf-8'
        return resp
    return response


def datetimeFilter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta//60)
    if delta<86400:
        return u'%s小时前' % (delta//3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)


def test(request):
    return web.Response(body='<h1>HELLO</h1>')


async def init(loop):
    logging.info("start server")
    await www.orm.createPool(loop=loop)
    app = web.Application(loop=loop,middlewares=[loggerFactory, responseFactory])
    init_jinja2(app,filter=dict(datetime=datetimeFilter))
    add_routes(app,'handles')
    add_static(app)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 8888)
    logging.info('server started at http://127.0.0.1:8888...')
    return srv
loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
