#!/usr/bin/python

import sys, os
import tornado.web
import urllib2
import logging
import json
import datetime

reload(sys)
sys.setdefaultencoding('utf8')
sys.path.append('..')
import common

API_TOKEN = 'FSUZWU8RKI'
WEATHER_API_URI = 'https://api.thinkpage.cn/v2/weather/all.json?language=zh-chs&unit=c&aqi=city&key=%s&city=%s'
WEATHER_API_URI = WEATHER_API_URI % (API_TOKEN, '%s')

logger = logging.getLogger('web')

class WeatherHandler(tornado.web.RequestHandler):

	city_list_from_thinkpage = None
	city_name_list = []
	city_name_cache = {}

	@classmethod
	def cache(cls):
		filename = common.get_file_from_current_dir(__file__, 'city_list_from_thinkpage.json')
		if not os.path.exists(filename):
			logger.error('Missing file \'city_list_from_thinkpage.json\'')
			return
		try:
			city_list_from_thinkpage_file = open(filename, 'r')
			city_list_from_thinkpage_content = city_list_from_thinkpage_file.read()
			city_list_from_thinkpage = json.loads(city_list_from_thinkpage_content)
			if city_list_from_thinkpage is None:
				raise Exception('city_list_from_thinkpage is None')
		except Exception, e:
			logger.error('Failed to read the file (city_list_from_thinkpage.json), error: %s' % e)
		finally:
			if city_list_from_thinkpage_file is not None:
				city_list_from_thinkpage_file.close()
			return
		for _ in city_list_from_thinkpage[::-1]:
			id_ = _.get('id')
			if id_ is not None and id_.startswith('CH'):
				name = _.get('name')
				if name is not None:
					city_name_list.append(name)
				
	def name_parse(self, city_name):
		city_strict_name = city_name_cache.get(city_name)
		if city_strict_name is not None:
			return city_strict_name
		for _ in city_name_list:
			if _ in city_name:
				city_name_cache[city_name] = _
				return _

	def get(self):

		logger.debug('request info') # TODO

		city_name = self.get_argument('city')
		if city_name is None or len(city_name) == 0:
			self.write(201)
			return
		city_name = self.name_parse(city_name)
		content_from_api = None
		try:
			response = urllib2.urlopen(WEATHER_API_URI % city_name)
			content_from_api = response.read()
			response.close()
		except Exception, e:
			logger.error('HTTP request error, error: (%s)' % e)
			self.write(501)
			return
		if content_from_api is None or len(content_from_api) == 0:
			logger.error('Response data exception (from thinkpage.cn), length: %s, error: %s' % (len(content_from_api), e))
			self.write(501)
			return
		object_from_api = None
		try:
			object_from_api = json.loads(content_from_api)
			if object_from_api is None:
				raise Exception('object_from_api is None')
		except Exception, e:
			logger.error('Response data format exception (from thinkpage.cn), length: %s, error: %s' % (len(content_from_api), e))
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

		hightemp = None
		wind = None
		img = None # TODO
		weather = None
		lowtemp = None
		sksd = None
		skhour = None
		skmin = None
		month = None
		year = None
		day = None
		sktemp = None
		index_xc = None
		pm25 = None
		
		weather = object_from_api.get('weather')
		futures = None
		if weather is not None and len(weather) > 0:
			weather = weather[0]
			now = weather.get('now')
			if now is not None:
				sktemp = sksd = now.get('humidity')
				air_quality = now.get('air_quality')
				if air_quality is not None:
					city_air_quality = air_quality.get('city')
					pm25 = city_air_quality.get('pm25')
			futures = weather.get('future')
			if futures is not None and len(futures) > 0:
				future_0 = futures[0]
				hightemp = future_0.get('high')
				wind = future_0.get('wind')
				weather = future_0.get('text')
				lowtemp = future_0.get('low')
			today = weather.get('today')
			if today is not None:
				suggestion = today.get('suggestion')
				if suggestion is not None:
					car_washing = suggestion.get('car_washing')
					if car_washing is not None:
						index_xc = car_washing.get('brief')
		img = None # TODO
		now_time = datetime.datetime.now()
		skhour = now_time.hour
		skmin = now_time.minute
		month = now_time.month
		year = now_time.year
		day = now_time.day

		res = '{ '
		res_today_section = '"today": { ' +
			'"hightemp": "%s", ' % hightemp +
			'"wind": "%s", ' % wind +
			'"img": "%s", ' % img + # TODO WTF
			'"weather": "%s", ' % weather +
			'"lowtemp": "%s", ' % lowtemp +
			'"sksd": "%s", ' % sksd +
			'"skhour": %s, ' % skhour +
			'"skmin": %s, ' % skmin +
			'"month": %s, ' % month +
			'"year": %s, ' % year +
			'"day": %s, ' % day +
			'"sktemp": %s, ' % sktemp +
			'"index_xc": "%s"' % index_xc +
			' }, '
		res += res_today_section
		res_future_section = '"future": [ '
		if futures is not None:
			res_future_section_in = []
			for _ in futures:
				hightemp_ = None
				wind_ = None
				img_ = None
				weather_ = None
				lowtemp_ = None

				hightemp_ = _.get('high')
				wind_ = _.get('wind')
				img_ = None # TODO
				weather_ = _.get('text')
				lowtemp_ = _.get('low')

				res_future_section_in.append('{ ' +
					'"hightemp": "%s", ' % hightemp_ +
					'"wind": "%s", ' % wind_ +
					'"img": "%s", ' % img_ + # TODO WTF
					'"weather": "%s", ' % weather_ +
					'"lowtemp": "%s"' % lowtemp_ +
					' }')
			res_future_section += ','.join(res_future_section_in)
		res_future_section += ' ], '
		res += res_future_section

		res_pm_25 = '"pm2.5": %s, ' % pm25
		res += res_pm_25
		#res_sutime = '"sutime": %s, ' % sutime
		#res += res_sutime
		res_city = '"city": "%s"' % city_name
		res += ' }'
		self.write(res)
			
	
		









	
