#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Ten Tsang'

# fabfile.py
import os
import re
from datetime import datetime

# 导入Fabric API：
from fabric.api import *

# 服务器登录用户名：
env.user = 'ten'
env.password = '123456'
# sudo用户为root：
env.sudo_user = 'root'
# 服务器地址，可以有多个，一次部署：
env.hosts = ['192.168.168.247']

# 服务器MySQL用户名和口令：
db_user = 'root'
db_password = '123456'

def _now():
	return datetime.now().strftime('%y-%m-%d_%H.%M.%S')

def _current_path():
	return os.path.abspath('.')

_TAR_FILE = 'dist-webform.tar.gz'

def build():
	includes = ['static', 'templates', '*.py']
	excludes = ['test', '.*', '*.pyc', '*.pyo']
	local('rm -f dist/%s' % _TAR_FILE)
	with lcd(os.path.join(_current_path(), 'www')):
		cmd = ['tar', '--dereference', '-czvf', '../dist/%s' % _TAR_FILE]
		cmd.extend(['--exclude=\'%s\'' % ex for ex in excludes])
		cmd.extend(includes)
		local(' '.join(cmd), capture=False)

_REMOTE_TMP_TAR = '/tmp/%s' % _TAR_FILE
_REMOTE_BASE_DIR = '/srv/web-form'

def deploy():
	newdir = 'www-%s' % _now()
	# 删除已有的tar文件：
	run('rm -f %s' % _REMOTE_TMP_TAR)
	# 上传新的tar文件：
	put('dist/%s' % _TAR_FILE, _REMOTE_TMP_TAR)
	# 创建新目录：
	with cd(_REMOTE_BASE_DIR):
		sudo('mkdir %s' % newdir)
	# 解压到新目录：
	with cd('%s/%s' % (_REMOTE_BASE_DIR, newdir)):
		sudo('tar -xzvf %s' % _REMOTE_TMP_TAR)
	# 重置软链接：
	with cd(_REMOTE_BASE_DIR):
		sudo('rm -f www')
		sudo('ln -s %s www' % newdir)
		sudo('chown ten:ten www')
		sudo('chown -R ten:ten %s' % newdir)
	# 重启Python服务和Nginx服务器：
	with settings(warn_only=True):
		sudo('supervisorctl stop web-form')
		sudo('supervisorctl start web-form')
		sudo('/etc/init.d/nginx reload')

