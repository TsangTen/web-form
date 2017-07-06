#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Ten Tsang'

import time
import uuid
from orm import Model, StringField, BooleanField, FloatField

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
	recognition = BooleanField()
	block_from_beginning = BooleanField()
	block_at_midway = BooleanField()
	bug = StringField(ddl='varchar(500)')
	remarks = StringField(ddl='varchar(500)')
	user_name = StringField(ddl='varchar(50)')
	created_at = FloatField(default=time.time)
		
		