#!/usr/bin/python

import sys, os, threading
import tornado.web
import tornado.httpclient
import tornado.gen
import urllib2
import logging
import json
import datetime

reload(sys)
sys.setdefaultencoding('utf8')
sys.path.append('..')
import common
import config

WEATHER_API_URI = 'https://api.thinkpage.cn/v2/weather/all.json?language=zh-chs&unit=c&aqi=city&key=%s&city=%s'
WEATHER_API_URI = WEATHER_API_URI % (config.THINKPAGE_CN_API_TOKEN, '%s')

logger = logging.getLogger('web')

interval = datetime.timedelta(minutes=59)

class WeatherHandler(tornado.web.RequestHandler):

	city_list_from_thinkpage = None
	city_name_list = []
	city_name_cache = {} # TODO persistence
	city_name_result_map = {} # TODO persistence

	img_code_map = {}

	@classmethod
	def cache(cls):
		city_list_from_thinkpage_filename = \
			common.get_file_from_current_dir(__file__, 'city_list_from_thinkpage.json')
		if not os.path.exists(city_list_from_thinkpage_filename):
			logger.error('Missing file \'city_list_from_thinkpage.json\'')
			return
		try:
			city_list_from_thinkpage_file = open(city_list_from_thinkpage_filename, 'r')
			city_list_from_thinkpage_content = city_list_from_thinkpage_file.read()
			cls.city_list_from_thinkpage = json.loads(city_list_from_thinkpage_content)
			if cls.city_list_from_thinkpage is None:
				raise Exception('city_list_from_thinkpage is None')
		except Exception, e:
			logger.error('Failed to read the file (city_list_from_thinkpage.json), error: %s' % e)
		finally:
			if city_list_from_thinkpage_file is not None:
				city_list_from_thinkpage_file.close()
		for _ in cls.city_list_from_thinkpage[::-1]:
			id_ = _.get('id')
			if id_ is not None and id_.startswith('CH'):
				name = _.get('name')
				if name is not None:
					cls.city_name_list.append(name)

		# img code
		
		img_code_map_filename = \
			common.get_file_from_current_dir(__file__, 'img_code_map.json')
		if not os.path.exists(img_code_map_filename):
			logger.error('Missing file \'img_code_map.json\'')
			return
		try:
			img_code_map_file = open(img_code_map_filename, 'r')
			img_code_map_content = img_code_map_file.read()
			img_code_map = json.loads(img_code_map_content)
			if img_code_map is None:
				raise Exception('img_code_map is None')
			cls.img_code_map = img_code_map
		except Exception, e:
			logger.error('Failed to read the file (img_code_map.json), error: %s' % e)
		finally:
			if img_code_map_file is not None:
				img_code_map_file.close()
				
	def name_parse(self, city_name):
		city_strict_name = WeatherHandler.city_name_cache.get(city_name)
		if city_strict_name is not None:
			return city_strict_name
		for _ in WeatherHandler.city_name_list:
			if _ in city_name:
				WeatherHandler.city_name_cache[city_name] = _
				return _

	def transform_img_code(self, code):
		if code is None:
			code = '0'
		if isinstance(code, basestring) and len(code) == 0:
			code = '0'
		if isinstance(code, int):
			code = str(code)
		new_code = WeatherHandler.img_code_map.get(code)
		return new_code

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

		city_name = None
		if self.request.arguments.has_key('city'):
			city_name = self.get_argument('city')
		if city_name is None or len(city_name) == 0:
			logger.error('Missing argument \'city\'')
			self.write(201)
			return
		raw_city_name = city_name
		city_name = self.name_parse(city_name)
		if city_name is None or len(city_name) == 0:
			logger.error('No matching area name (%s)' % raw_city_name)
			self.write(201)
			return
		res_box = WeatherHandler.city_name_result_map.get(city_name)
		if res_box is not None:
			res_ = res_box.get('res')
			time_ = res_box.get('time')
			if res_ is not None and time_ is not None and datetime.datetime.now() < time_ + interval:
				now_time = datetime.datetime.now()
				skhour = now_time.hour
				skmin = now_time.minute
				month = now_time.month
				year = now_time.year
				day = now_time.day
				res_ = res_ % (
					skhour,
					skmin,
					month,
					year,
					day,
					raw_city_name)
				if config.Mode == 'DEBUG' and pretty_state is not None and pretty_state:
					res_ = common.pretty_print(res_)
				self.write(res_)
				return
		content_from_api = None
		try:
			http_client = tornado.httpclient.AsyncHTTPClient()
			response = yield http_client.fetch(WEATHER_API_URI % city_name)
			content_from_api = response.body
		except Exception, e:
			logger.error('HTTP request error (from thinkpage.cn), %s' % e)
			self.write(501)
			return
		finally:
			http_client.close()
		if content_from_api is None or len(content_from_api) == 0:
			logger.error('Response data exception (from thinkpage.cn), %s' % e)
			self.write(501)
			return
		object_from_api = None
		try:
			object_from_api = json.loads(content_from_api)
			if object_from_api is None:
				raise Exception('object_from_api is None')
		except Exception, e:
			logger.error('JSON parse failure (from thinkpage.cn), %s' % e)
			self.write(501)
			return
		status = object_from_api.get('status')
		if status is None:
			logger.error('Field \'status\' not found')
			self.write(501)
			return
		if status <> 'OK':
			logger.error('Service status is not equal to \'OK\' (from thinkpage.cn)')
			self.write(501)
			return

		hightemp = '0' + u"\u2103"
		wind = ''
		img = '[]'
		weather_text = ''
		lowtemp = '0' + u"\u2103"
		sksd = ''
		skhour = 0
		skmin = 0
		month = 0
		year = 0
		day = 0
		sktemp = '0' + u"\u2103"
		index_xc = ''
		pm25 = 0
		
		weather = object_from_api.get('weather')
		futures = None
		if weather is not None and len(weather) > 0:
			weather = weather[0]
			now = weather.get('now')
			if now is not None:
				sktemp = now.get('temperature')
				if sktemp is None:
					sktemp = '0'
				sktemp += u"\u2103"
				sksd = now.get('humidity')
				if sksd is None:
					sksd = ''
				air_quality = now.get('air_quality')
				if air_quality is not None:
					city_air_quality = air_quality.get('city')
					if city_air_quality is not None:
						pm25 = city_air_quality.get('pm25')
			futures = weather.get('future')
			if futures is not None and len(futures) > 0:
				future_0 = futures[0]
				hightemp = future_0.get('high')
				if hightemp is None:
					hightemp = '0'
				hightemp += u"\u2103"
				wind = future_0.get('wind')
				if wind is None:
					wind = ''
				weather_text = future_0.get('text')
				if weather_text is None:
					weather_text = ''
				lowtemp = future_0.get('low')
				if lowtemp is None:
					lowtemp = '0'
				lowtemp += u"\u2103"
				code1 = future_0.get('code1')
				if code1 is None:
					code1 = '0'
				code2 = future_0.get('code2')
				if code2 is None:
					code2 = '0'
				img = '["%s", "%s"]' % (
					self.transform_img_code(code1), 
					self.transform_img_code(code2)
				)
			today = weather.get('today')
			if today is not None:
				suggestion = today.get('suggestion')
				if suggestion is not None:
					car_washing = suggestion.get('car_washing')
					if car_washing is not None:
						index_xc = car_washing.get('brief')
						if index_xc is None:
							index_xc = ''

		res = '{ '
		res_today_section = ('"today": { ' +
			'"hightemp": "%s", ' % hightemp +
			'"wind": "%s", ' % wind +
			'"img": %s, ' % img +
			'"weather": "%s", ' % weather_text +
			'"lowtemp": "%s", ' % lowtemp +
			'"sksd": "%s", ' % sksd +
			#'"skhour": %s, ' % skhour +
			#'"skmin": %s, ' % skmin +
			#'"month": %s, ' % month +
			#'"year": %s, ' % year +
			#'"day": %s, ' % day +
			'"skhour": %s, ' +
			'"skmin": %s, ' +
			'"month": %s, ' +
			'"year": %s, ' +
			'"day": %s, ' +
			'"sktemp": "%s", ' % sktemp +
			'"index_xc": "%s"' % index_xc +
			' }, ')
		res += res_today_section
		res_future_section = '"future": [ '
		if futures is not None:
			res_future_section_in = []
			first__ = True
			for _ in futures:
				if first__:
					first__ = False
					continue
				hightemp_ = '0' + u"\u2103"
				wind_ = ''
				img_ = '[]'
				weather_ = ''
				lowtemp_ = '0' + u"\u2103"

				hightemp_ = _.get('high')
				if hightemp_ is None:
					hightemp_ = '0'
				hightemp_ += u"\u2103"
				wind_ = _.get('wind')
				if wind_ is None:
					wind_ = ''
				code1 = _.get('code1')
				if code1 is None:
					code1 = '0'
				code2 = _.get('code2')
				if code2 is None:
					code2 = '0'
				img_ = '["%s", "%s"]' % (
					self.transform_img_code(code1), 
					self.transform_img_code(code2)
				)
				weather_ = _.get('text')
				if weather_ is None:
					weather_ = ''
				lowtemp_ = _.get('low')
				if lowtemp_ is None:
					lowtemp_ = '0'
				lowtemp_ += u"\u2103"

				res_future_section_in.append(('{ ' +
					'"hightemp": "%s", ' % hightemp_ +
					'"wind": "%s", ' % wind_ +
					'"img": %s, ' % img_ +
					'"weather": "%s", ' % weather_ +
					'"lowtemp": "%s"' % lowtemp_ +
					' }'))
			res_future_section += ','.join(res_future_section_in)
		res_future_section += ' ], '
		res += res_future_section

		if pm25 is None:
			pm25 = 0
		res_pm_25 = '"pm2.5": %s, ' % pm25
		res += res_pm_25
		#res_sutime = '"sutime": %s, ' % sutime
		#res += res_sutime
		res_city = '"city": "%s"'
		res += res_city
		res += ' }'
		WeatherHandler.city_name_result_map[city_name] = {
			'res': res,
			'time': datetime.datetime.now()
		}
		now_time = datetime.datetime.now()
		skhour = now_time.hour
		skmin = now_time.minute
		month = now_time.month
		year = now_time.year
		day = now_time.day
		res = res % (
			skhour,
			skmin,
			month,
			year,
			day,
			raw_city_name)
		if config.Mode == 'DEBUG' and pretty_state is not None and pretty_state:
			res = common.pretty_print(res)
		self.write(res)
			
	def write(self, trunk):
		if type(trunk) == int:
			trunk = str(trunk)
		super(WeatherHandler, self).write(trunk)
		
		









	
