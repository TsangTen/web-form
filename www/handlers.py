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
from models import User, Reports, Records, next_id, Daily
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

def get_record(row, keys):
	line = list()
	for key in keys:
		if key == 'created_at':
			dt = datetime.fromtimestamp(row[key])
			line.append('%s-%s-%s' % (dt.year, dt.month, dt.day))
			continue
		else:
			line.append(row[key])
	return line

def sheet2html(row, keys):
	l = get_record(row, keys)
	line = map(
		lambda s: '<td>%s</td>' % str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'),
		l
	)
	return ''.join(line)

def sheet2list(row, keys):
	l = get_record(row, keys)
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

def get_col_name(names):
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
	report.html_sheet = report.html_sheet + get_col_name(names) + '</tr>'
	report.csv = [names,]
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
	for record in records:
		report.csv.append(sheet2list(record, record_keys))
		# logging.info('Type: %s\nRow: %s' %(type(record), record))
		record.html_sheet = sheet2html(record, record_keys)
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
	return report

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
	records = await Records.findAll('report_id=?', [id], orderBy='created_at desc')
	for r in records:
		record = await Records.find(r['id'])
		if record is None:
			raise APIResourceNotFoundError('Record', 'Not Found!')
		await record.remove()
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
	logging.info('---------------api create record------------------')
	user = request.__user__
	if user is None:
		raise APIPermissionError('Please signin first.')

	args = [
		major_class, app_name, rule, type_of_change,
		platform, test_env, recognition, block_from_beginning,
		block_at_midway, bug, remarks
	]
	for arg in args:
		if not arg or not arg.strip():
			raise APIValueError('%s' % arg, 'empty!')

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

daily_names = [
	'反馈时间',
	'反馈方式',
	'支持类型',
	'TD编号',
	'反馈人员',
	'问题描叙',
	'处理时间',
	'是否完成',
	'处理情况（问题的原因）',
	'消耗时间（人天）',
	'处理人'
]

@get('/daily/')
async def api_get_daily(request, *, page='1'):
	global daily_names
	page_index = get_page_index(page)
	Daily_report = type('Daily_report', (object,), dict())
	report = Daily_report
	report.id = int(time.time())
	report.title = '日报'
	report.html_content = '没有任何日报记录'
	report.created_at = time.time()
	num = await Daily.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return {
			'__template__': 'daily.html',
			'report': report
		}
	if request.__user__.admin:
		daily_records = await Daily.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	else:
		report.tilte = '%s的日报' % request.__user__.name
		work_id = request.__user__.work_id
		daily_records = await Daily.findAll('work_id=?', [work_id], orderBy='created_at desc')
		if not daily_records:
			return '没有您的日报记录'
	daily_keys = [
			'feedback_time', 
			'feedback_way', 
			'support_type', 
			'td_num', 
			'who_feedback', 
			'issue_desc', 
			'deal_time', 
			'finished', 
			'deal_desc', 
			'time_cost',
			'who'
		]
	report.html_sheet = '<table border="1">' + '<tr>'
	report.html_sheet = report.html_sheet + get_col_name(daily_names) + '</tr>'
	for record in daily_records:
		if record.finished:
			record.finished = '是'
		else:
			record.finished = '否'
		record.html_sheet = sheet2html(record, daily_keys)
		record.html_sheet = '<tr>' + record.html_sheet + '</tr>'
		report.html_sheet += record.html_sheet
	report.html_sheet += '</table>'
	report.html_content = markdown2.markdown(report.html_sheet)
	return {
		'__template__': 'daily.html',
		'report': report
	}

@post('/api/daily/{id}')
async def api_create_daily_record(
		id, request, *, 
		feedback_time, feedback_way, support_type, td_num, who_feedback, 
		issue_desc, deal_time, finished, deal_desc, time_cost
	):

	logging.info('---------------api create daily record------------------')
	user = request.__user__

	if user is None:
		raise APIPermissionError('Please signin first.')

	args = [
			feedback_time, feedback_way, support_type, td_num, who_feedback, 
			issue_desc, deal_time, finished, deal_desc, time_cost
		]
	for arg in args:
		if not arg or not arg.strip():
			raise APIValueError('%s' % arg, 'empty!')

	if finished == '是':
		finished = True
	else:
		finished = False

	daily = Daily(
			work_id=user.work_id,
			feedback_time=feedback_time,
			feedback_way=feedback_way,
			support_type=support_type,
			td_num=td_num,
			who_feedback=who_feedback,
			issue_desc=issue_desc,
			deal_time=deal_time,
			finished=finished,
			deal_desc=deal_desc,
			time_cost=time_cost,
			who=user.name
		)
	await daily.save()
	return daily