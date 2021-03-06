#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Ten Tsang'

import logging; logging.basicConfig(level=logging.INFO)
import os
import time
import asyncio
import json
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import orm
from config import configs
from coroweb import add_routes, add_static
from handlers import cookie2user, COOKIE_NAME

def init_jinja2(app, **kw):  # 初始化jinja2模板
	logging.info('Init jinja2...')
	options = dict(
		autoescape = kw.get('autoescape', True),
		auto_reload = kw.get('auto_reload', True),
		block_start_string = kw.get('block_start_string', '{%'),
		block_end_string = kw.get('block_end_string', '%}'),
		variable_start_string = kw.get('variable_start_string', '{{'),
		variable_end_string = kw.get('variable_end_string', '}}')
	)
	path = kw.get('path', None)
	if path is None:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
	logging.info('Set jinja2 templates path: %s' % path)
	env = Environment(loader=FileSystemLoader(path), **options)
	filters = kw.get('filters', None)
	if filters is not None:
		for key, value in filters.items():
			env.filters[key] = value
	app['__templating__'] = env


def time_filter(_time):
	delta_time = int(time.time() - _time)
	if delta_time < 60:
		return '1 minute ago.'
	elif delta_time < 3600:
		return '%s minutes ago.' % (delta_time // 60)
	elif delta_time < 86400:
		return '%s hours ago.' % (delta_time // 3600)
	elif delta_time < 604800:
		return '%s days age.' % (delta_time // 86400)
	else:
		dt = datetime.fromtimestamp(_time)
		return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

async def logger_factory(app, handler):
	async def logger(request):
		logging.info('Request: %s %s' % (request.method, request.path))
		# await asyncio.sleep(0.3)
		return (await handler(request))
	return logger

async def auth_factory(app, handler):
	async def auth(request):
		logging.info('check user: %s %s' % (request.method, request.path))
		request.__user__ = None
		cookie_str = request.cookies.get(COOKIE_NAME)
		if cookie_str:
			user = await cookie2user(cookie_str)
			if user:
				logging.info('Set current user: %s' % user.work_id)
				request.__user__ = user
		if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
			return web.HTTPFound('/signin')
		if request.path.startswith('/daily/') and request.__user__ is None:
			return web.HTTPFound('/signin')
		return (await handler(request))
	return auth

async def data_factory(app, handler):
	async def parse_data(request):
		if request.method == 'POST':
			if request.content_type.startswith('application/json'):
				request.__data__ = await request.json()
				logging.info('Request json: %s' % str(request.__data__))
			elif request.content_type.startswith('application/x-www-form-urlencoded'):
				request.__data__ = await request.post()
				logging.info('Request form: %s' % str(request.__data__))
		return (await handler(request))
	return parse_data

async def response_factory(app, handler):
	async def response(request):
		logging.info('Response handler...')
		r = await handler(request)
		if isinstance(r, web.StreamResponse):
			return r
		if isinstance(r, bytes):
			resp = web.Response(body=r)
			resp.content_type = 'application/octect-stream'
			return resp
		if isinstance(r, str):
			if r.startswith('redirect'):
				return web.HTTPFound(r[9:])
			resp = web.Response(body=r.encode('utf-8'))
			resp.content_type = 'text/html;charset=utf-8'
			return resp
		if isinstance(r, dict):
			template = r.get('__template__')
			if template is None:
				resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o:o.__dict__).encode('utf-8'))
				resp.content_type = 'application/json;charset=utf-8'
				return resp
			else:
				r['__user__'] = request.__user__
				resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
				resp.content_type = 'text/html;charset=utf-8'
				return resp
		if isinstance(r, int) and r >= 100 and r < 600:
			return web.Response(r)
		if isinstance(r, tuple) and len(r) == 2:
			t, m = r
			if isinstance(t, int) and t >= 100 and t < 600:
				return web.ReferenceError(t, str(m))
		resp = web.Response(body=str(r).encode('utf-8'))
		resp.content_type = 'text/plain;charset=utf-8'
		return resp
	return response

async def init(loop):
	await orm.create_pool(loop=loop, **configs.db)
	app = web.Application(loop=loop, middlewares=[
		logger_factory, auth_factory, response_factory
	])
	init_jinja2(app, filters=dict(datetime=time_filter))
	add_routes(app, 'handlers')
	add_static(app)
	srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
	logging.info('Server started at http://127.0.0.1:9000...')
	return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
