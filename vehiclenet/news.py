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

reload(sys)
sys.setdefaultencoding('utf8')
sys.path.append('..')
import common
import config

BAIDU_NEWS_URI = 'http://news.baidu.com/ns?tn=newstitle&word=%s'

logger = logging.getLogger('web')

interval = datetime.timedelta(minutes=20)

class NewsHandler(tornado.web.RequestHandler):

	news_key_result_map = {} # TODO persistence

	@tornado.gen.coroutine
	def get(self):

		pretty_state = False
		if config.Mode == 'DEBUG':
			logger.debug('Request URI: %s (%s)' % (self.request.uri, self.request.remote_ip))
			if self.request.arguments.has_key('pretty'):
				pretty_state = self.get_argument('pretty')

		if config.Mode == 'DEBUG' and pretty_state is not None and pretty_state:
			self.set_header('Content-Type', 'text/html; charset=UTF-8')
		else:
			self.set_header('Content-Type', 'application/json; charset=UTF-8')

		key = None
		if self.request.arguments.has_key('key'):
			key = self.get_argument('key')
		if key is None or len(key) == 0:
			logger.error('Missing argument \'key\'')
			self.write(-2)
			return
		res_box = NewsHandler.news_key_result_map.get(key)
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
			encode_key = key.encode('utf-8')
			encode_key = urllib2.quote(encode_key)
			response = yield http_client.fetch(BAIDU_NEWS_URI % key)
			content_from_api = response.body
		except Exception, e:
			logger.error('HTTP request error (from news.baidu.com), %s' % e)
			self.write(-1)
			return
		if content_from_api is None or len(content_from_api) == 0:
			logger.error('Response data exception (from news.baidu.com), %s' % e)
			self.write(-1)
			return
		object_from_api = None
		try:
			object_from_api = BeautifulSoup(content_from_api, 'html5lib')
			if object_from_api is None:
				raise Exception('object_from_api is None')
		except Exception, e:
			logger.error('HTML parse failure (from news.baidu.com), %s' % e)
			self.write(-2)
			return
		res = '{ '
		res += '"result": ['
		news_id_list = []
		titles_h3 = object_from_api.select('h3[class="c-title"]')
		if titles_h3 is not None and len(titles_h3) > 0:
			titles_ = []
			for _ in titles_h3:
				link_ = _.a
				if link_ is not None:
					href_ = link_.get('href')
					if href_ is None:
						href_ = ''
					text_ = link_.get_text()
					if text_ is None:
						text_ = ''
					title_ = ('{ ' +
						'"url": "%s", ' % href_ +
						'"title": "%s"' % text_ +
						' }')
					titles_.append(title_)
			if titles_ is not None and len(titles_) > 0:
				titles_str = ','.join(titles_)
				res += titles_str
		res += ']'
		res += ' }'
		NewsHandler.news_key_result_map[key] = {
			'res': res,
			'time': datetime.datetime.now()
		}
		if config.Mode == 'DEBUG' and pretty_state is not None and pretty_state:
			res = common.pretty_print(res)
		self.write(res)


	def write(self, trunk):
		if type(trunk) == int:
			trunk = str(trunk)
		super(NewsHandler, self).write(trunk)
