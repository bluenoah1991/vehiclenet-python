#!/usr/bin/python

import os

VERSION = '1.0.0'

Mode = 'DEBUG'
#Mode = 'RELEASE'

THINKPAGE_CN_API_TOKEN = os.getenv('THINKPAGE_CN_API_TOKEN')
if THINKPAGE_CN_API_TOKEN is None:
	THINKPAGE_CN_API_TOKEN = ''
