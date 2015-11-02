#!/usr/bin/python

import sys, os, threading
import tornado.web
import tornado.httpclient
import tornado.gen
import urllib2
import logging
from bs4 import BeautifulSoup
import json
import datetime
import re

reload(sys)
sys.setdefaultencoding('utf8')
sys.path.append('..')
import common
import config

BAIDU_LRC_URI = 'http://music.baidu.com/search/lrc?key=%s'

logger = logging.getLogger('web')

interval = datetime.timedelta(minutes=59)

class LrcSearchHandler(tornado.web.RequestHandler):

	song_name_result_map = {} # TODO persistence

	@tornado.gen.coroutine
	def get(self):

		pretty_state = False
		if config.Mode == 'DEBUG':
			logger.debug('Request URI: %s' % self.request.uri)
			if self.request.arguments.has_key('pretty'):
				pretty_state = self.get_argument('pretty')

		if config.Mode == 'DEBUG' and pretty_state is not None and pretty_state:
			self.set_header('Content-Type', 'text/html; charset=UTF-8')
		else:
			self.set_header('Content-Type', 'application/json; charset=UTF-8')

		song_name = None
		if self.request.arguments.has_key('song'):
			song_name = self.get_argument('song')
		if song_name is None or len(song_name) == 0:
			logger.error('Missing argument \'song\'')
			self.write(-2)
			return
		res_box = LrcSearchHandler.song_name_result_map.get(song_name)
		if res_box is not None:
			res_ = res_box.get('res')
			time_ = res_box.get('time')
			if res_ is not None and time_ is not None and datetime.datetime.now() < time_ + interval:
				if config.Mode == 'DEBUG' and pretty_state is not None and pretty_state:
					res_ = common.pretty_print(res_)
				self.write(res_)
				return
		content_from_api = None
		try:
			http_client = tornado.httpclient.AsyncHTTPClient()
			response = yield http_client.fetch(BAIDU_LRC_URI % song_name)
			content_from_api = response.body
		except Exception, e:
			logger.error('HTTP request error (from music.baidu.com/search/lrc), %s' % e)
			self.write(-1)
			return
		if content_from_api is None or len(content_from_api) == 0:
			logger.error('Response data exception (from music.baidu.com/search/lrc), %s' % e)
			self.write(-1)
			return
		object_from_api = None
		try:
			object_from_api = BeautifulSoup(content_from_api, 'html5lib')
			if object_from_api is None:
				raise Exception('object_from_api is None')
		except Exception, e:
			logger.error('HTML parse failure (from music.baidu.com/search/lrc), %s' % e)
			self.write(-2)
			return
		res = None
		down_lrc_btn = object_from_api.select('a[class~="down-lrc-btn"]')
		if down_lrc_btn is not None and len(down_lrc_btn) > 0:
			down_lrc_btn = down_lrc_btn[0]
			attr_class = down_lrc_btn.get('class')
			attr_str = None
			if attr_class is not None and len(attr_class) > 0:
				attr_str = ''.join(attr_class) # TODO Maybe correct
			if attr_str is not None and len(attr_str) > 0:
				match_ = re.search("'href' {0,1}: {0,1}'([^']+)'", attr_str)
				if match_ is not None:
					href = match_.group(1)
					if href is not None and len(href) > 0:
						if href.endswith('.lrc'):
							res = 'http://ting.baidu.com' + href 
		LrcSearchHandler.song_name_result_map[song_name] = {
			'res': res,
			'time': datetime.datetime.now()
		}
		if config.Mode == 'DEBUG' and pretty_state is not None and pretty_state:
			res = common.pretty_print(res)
		self.write(res)


	def write(self, trunk):
		if type(trunk) == int:
			trunk = str(trunk)
		super(LrcSearchHandler, self).write(trunk)
