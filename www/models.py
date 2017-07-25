#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Ten Tsang'

import time
import uuid
from orm import Model, StringField, BooleanField, FloatField, IntegeField

def next_id():
	return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
	__table__ = 'users'

	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	work_id = StringField(ddl='varchar(50)')
	passwd = StringField(ddl='varchar(50)')
	admin = BooleanField()
	name = StringField(ddl='varchar(50)')
	created_at = FloatField(default=time.time)

class Reports(Model):
	__table__ = 'reports'

	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	title = StringField(ddl='varchar(100)')
	created_at = FloatField(default=time.time)

class Records(Model):
	__table__ = 'records'

	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	report_id = StringField(ddl='varchar(50)')
	major_class = StringField(ddl='varchar(50)')
	app_name = StringField(ddl='varchar(50)')
	rule = StringField(ddl='varchar(50)')
	type_of_change = StringField(ddl='varchar(50)')
	platform = StringField(ddl='varchar(50)')
	test_env = StringField(ddl='varchar(50)')
	recognition = StringField(ddl='varchar(50)')
	block_from_beginning = StringField(ddl='varchar(50)')
	block_at_midway = StringField(ddl='varchar(50)')
	bug = StringField(ddl='varchar(500)')
	remarks = StringField(ddl='varchar(500)')
	user_name = StringField(ddl='varchar(50)')
	created_at = FloatField(default=time.time)

class Daily(Model):
	__table__ = 'daily'

	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	work_id = StringField(ddl='varchar(50)')
	feedback_time = StringField(ddl='varchar(50)')
	feedback_way = StringField(ddl='varchar(50)')
	support_type = StringField(ddl='varchar(50)')
	td_num = IntegeField()
	who_feedback = StringField(ddl='varchar(50)')
	issue_desc = StringField(ddl='varchar(100)')
	deal_time = StringField(ddl='varchar(50)')
	finished = BooleanField()
	deal_desc = StringField(ddl='varchar(200)')
	time_cost = FloatField()
	who = StringField(ddl='varchar(50)')
	created_at = FloatField(default=time.time)
	