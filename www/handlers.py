#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Ten Tsang'

import re
import time
import json
import logging
import hashlib
import base64
import asyncio
from aiohttp import web
from datetime import datetime

import markdown2
from coroweb import get, post
from apis import APIValueError, APIResourceNotFoundError, APIError, Page,APIPermissionError
from models import User, Reports, Records, next_id
from config import configs

COOKIE_NAME = 'webform'
_COOKIE_KEY = configs.session.secret

def check_admin(request):
	if request.__user__ is None or not request.__user__.admin:
		raise APIPermissionError()

def get_page_index(page_str):
	p = 1
	try:
		p = int(page_str)
	except ValueError as e:
		pass
	if p < 1:
		p = 1
	return p

# 计算加密cookie
def user2cookie(user, max_age):
	'''
		Generate cookie str by user.
	'''
	# build cookie string by: id-expires-sha1
	expires = str(int(time.time() + max_age))
	s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
	L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)

def text2html(text):
	lines = map(
		lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), 
		filter(lambda s: s.strip() != '', text.split('\n'))
	)
	return ''.join(lines)

record_keys = [
	'major_class',
	'app_name',
	'rule',
	'type_of_change',
	'platform',
	'test_env',
	'recognition',
	'block_from_beginning',
	'block_at_midway',
	'bug',
	'remarks',
	'user_name',
	'created_at'
]

def get_record(row):
	line = list()
	for key in record_keys:
		if key == 'created_at':
			dt = datetime.fromtimestamp(row[key])
			line.append('%s-%s-%s' % (dt.year, dt.month, dt.day))
			continue
		else:
			line.append(row[key])
	return line

def sheet2html(row):
	l = get_record(row)
	line = map(
		lambda s: '<td>%s</td>' % str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'),
		l
	)
	return ''.join(line)

def sheet2list(row):
	l = get_record(row)
	line = map(str, l)
	return list(line)

# 解密cookie
async def cookie2user(cookie_str):
	'''
		Parse cookie and load user if cookie is valid
	'''
	if not cookie_str:
		return None
	try:
		L = cookie_str.split('-')
		if len(L) != 3:
			return None
		uid, expires, sha1 = L
		if int(expires) < time.time():
			return None
		user = await User.find(uid)
		if user is None:
			return None
		s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('invalid sha1')
			return None
		user.passwd = '******'
		return user
	except Exception as e:
		logging.exception(e)
		return None

@get('/')
async def index(request):
	# reports = [
	#  	Reports(id='1', title='Test1', created_at=time.time()-120),
	# 	Reports(id='2', title='Report2', created_at=time.time()-3600),
	#  	Reports(id='3', title='There\'s no 3', created_at=time.time()-7200)
	# ]
	reports = await Reports.findAll()
	return {
		'__template__': 'index.html',
		'reports': reports
	}

names = [
	'大类',
	'应用',
	'规则',
	'改动类型',
	'平台类型',
	'测试环境',
	'识别效果',
	'开始封堵',
	'中途封堵',
	'bug',
	'备注',
	'测试人',
	'日期'
]

def get_col_name():
	global names
	l = list()
	for name in names:
		l.append('<td>' + name + '</td>')
	return ''.join(l)

@get('/report/{id}')
async def get_report(id):
	global names
	report = await Reports.find(id)
	records = await Records.findAll('report_id=?', [id], orderBy='created_at desc')
	report.html_sheet = '<table border="1">' + '<tr>'
	report.html_sheet = report.html_sheet + get_col_name() + '</tr>'
	report.csv = [names,]
	for record in records:
		report.csv.append(sheet2list(record))
		# logging.info('Type: %s\nRow: %s' %(type(record), record))
		record.html_sheet = sheet2html(record)
		record.html_sheet = '<tr>' + record.html_sheet + '</tr>'
		# logging.info(record.html_sheet)
		report.html_sheet += record.html_sheet
	report.html_sheet += '</table>'
	report.html_content = markdown2.markdown(report.html_sheet)
	
	return {
		'__template__': 'report.html',
		'report': report,
		'records': records
	}

@get('/api/users')
async def api_get_users(*, page='1'):
	page_index = get_page_index(page)
	num = await User.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, users=())
	users = await User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	for u in users:
		u.password = '******'
	return dict(page=p, users=users)

@get('/register')
def register():
	return {
		'__template__': 'register.html'
	}

@get('/signin')
def signin():
	return {
		'__template__': 'signin.html'
	}

@get('/signout')
def signout(request):
	referer = request.headers.get('Referer')
	r = web.HTTPFound(referer or '/')
	r.set_cookie(COOKIE_NAME, '-delete-', max_age=0, httponly=True)
	logging.info('user signed out.')
	return r

_RE_WORKID = re.compile(r'^[0-9]{5}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

@post('/api/users')
async def api_register_user(*, work_id, name, passwd):
	# logging('-----------------------------------------------')
	if not name or not name.strip():
		raise APIValueError('name', 'Invalid name.')
	if not work_id or not _RE_WORKID.match(work_id):
		raise APIValueError('work_id', 'Invalid work_id.')
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('passwd', 'Invalid passwd.')
	users = await User.findAll('work_id=?', [work_id])
	if len(users) > 0:
		raise APIError('register: failed', 'work_id', 'Work_id is already in use.')
	uid = next_id()
	sha1_passwd = '%s:%s' % (uid, passwd)
	user = User(
		id=uid, 
		name=name.strip(), 
		work_id=work_id, 
		passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest()
	)
	# logging.info("PPPPPPPPPPPPassword: %s" % user.password)
	await user.save()
	# make session cookie:
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@post('/api/authenticate')
async def authenticate(*, work_id, passwd):
	if not work_id:
		raise APIValueError('work_id', 'Invalid work_id.')
	if not passwd:
		raise APIValueError('passwd', 'Invalid passwd')
	users = await User.findAll('work_id=?', [work_id])
	if len(users) == 0:
		raise APIValueError('work_id', 'work_id not exist.')
	user = users[0]
	# check passwd:
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd', 'Invalid passwd.')
	# authenticate ok, set cookie:
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@post('/api/reports')
async def api_create_report(request, *, title):
	# logging.info('func:api_create_report')
	check_admin(request)
	if not title or not title.strip():
		raise APIValueError('title', 'title cannot be empty.')
	report = Reports(
			title=title.strip()
		)
	await report.save()
	return 'redirect:/manage/reports'

@post('/api/reports/{id}')
async def api_update_report(id, request, *, title):
	# logging.info('*********************')
	check_admin(request)
	report = await Reports.find(id)
	if not title or not title.strip():
		raise APIValueError('title', 'title cannot be empty.')
	report.title = title.strip()
	await report.update()
	return report

@post('/api/reports/{id}/delete')
async def api_delete_report(request, *, id):
	check_admin(request)
	report = await Reports.find(id)
	await report.remove()
	return dict(id=id)

@get('/api/reports')
async def api_reports(*, page='1'):
	page_index = get_page_index(page)
	num = await Reports.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, reports=())
	reports = await Reports.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	return dict(page=p, reports=reports)

@get('/api/reports/{id}')
async def api_get_report(*, id):
	report = await Reports.find(id)
	return report

@get('/manage/')
def manage():
	return 'redirect:/manage/reports'

@get('/manage/records')
def manage_records(*, page='1'):
	return {
		'__template__': 'manage_records.html',
		'page_index': get_page_index(page)
	}

@get('/manage/reports')
def manage_reports(*, page='1'):
	return {
		'__template__': 'manage_reports.html',
		'page_index': get_page_index(page)
	}

@get('/manage/reports/create')
def manage_create_report():
	return {
		'__template__': 'manage_report_edit.html',
		'id': '',
		'action': '/api/reports'
	}

@get('/manage/reports/edit')
def manage_edit_report(*, id):
	return {
		'__template__': 'manage_report_edit.html',
		'id': id,
		'action': '/api/reports/%s' % id
	}

@get('/api/records')
async def api_records(*, page='1'):
	page_index = get_page_index(page)
	num = await Records.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, records=())
	records = await Records.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	return dict(page=p, records=records)

@post('/api/reports/{id}/records')
async def api_create_record(
		id, request, *, major_class, app_name, rule, type_of_change,
		platform, test_env, recognition, block_from_beginning,
		block_at_midway, bug, remarks
	):
	logging.info('---------------------------------==')
	user = request.__user__
	if user is None:
		raise APIPermissionError('Please signin first.')
	if not major_class or not major_class.strip():
		raise APIValueError('major_class', 'empty!')
	if not app_name or not app_name.strip():
		raise APIValueError('app_name', 'empty!')
	if not rule or not rule.strip():
		raise APIValueError('rule', 'empty!')
	if not type_of_change or not type_of_change.strip():
		raise APIValueError('type_of_change', 'empty!')
	if not platform or not platform.strip():
		raise APIValueError('platform', 'empty!')
	if not test_env or not test_env.strip():
		raise APIValueError('test_env', 'empty!')
	if not recognition or not recognition.strip():
		raise APIValueError('recognition', 'empty!')
	if not block_from_beginning or not block_from_beginning.strip():
		raise APIValueError('block_from_beginning', 'empty!')
	if not block_at_midway or not block_at_midway.strip():
		raise APIValueError('block_at_midway', 'empty!')
	if not bug or not bug.strip():
		raise APIValueError('bug', 'empty!')
	if not remarks or not remarks.strip():
		raise APIValueError('remarks', 'empty!')
	report = await Reports.find(id)
	if report is None:
		raise APIResourceNotFoundError('Report')
	
	record = Records(
		report_id=report.id, 
		major_class=major_class.strip(), 
		app_name=app_name.strip(), 
		rule=rule.strip(), 
		type_of_change=type_of_change.strip(),
		platform=platform.strip(),
		test_env=test_env.strip(),
		recognition=recognition.strip(),
		block_from_beginning=block_from_beginning.strip(),
		block_at_midway=block_at_midway.strip(),
		bug=bug.strip(),
		user_name = user.name,
		remarks=remarks.strip()
	)
	await record.save()
	return record

@post('/api/records/{id}/delete')
async def api_delete_records(id, request):
	check_admin(request)
	record = await Records.find(id)
	if record is None:
		raise APIResourceNotFoundError('Record', 'Not Found!')
	await record.remove()
	return dict(id=id)
