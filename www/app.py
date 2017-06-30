#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Ten Tsang'

import logging; logging.basicConfig(level=logging.INFO)
import os
import sys
import time
import asyncio
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

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


async def init(loop):
	await orm.create_pool(loop=loop, **configs.db)
	app = web.Application(loop=loop, middlewares=[])
	init_jinja2(app, filters=dict(datetime=time_filter))
	srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
	logging.info('Server started at http://127.0.0.1:9000...')
	return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()