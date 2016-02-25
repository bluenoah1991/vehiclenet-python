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

BAIDU_SEARCH_URI = 'http://music.baidu.com/search/song?key=%s'
BAIDU_SONGLINK_URI = 'http://play.baidu.com/data/music/songlink?songIds=%s'
BAIDU_SONGINFO_URI = 'http://play.baidu.com/data/music/songInfo?songIds=%s'

logger = logging.getLogger('web')

interval = datetime.timedelta(minutes=59)

class MusicSearchHandler(tornado.web.RequestHandler):

	song_name_result_map = {} # TODO persistence

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

		song_name = None
		if self.request.arguments.has_key('song'):
			song_name = self.get_argument('song')
		if song_name is None or len(song_name) == 0:
			logger.error('Missing argument \'song\'')
			self.write(-2)
			return
		res_box = MusicSearchHandler.song_name_result_map.get(song_name)
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
			song_encode_name = song_name.encode('utf-8')
			song_encode_name = urllib2.quote(song_encode_name)
			response = yield http_client.fetch(BAIDU_SEARCH_URI % song_encode_name)
			content_from_api = response.body
		except Exception, e:
			logger.error('HTTP request error (from music.baidu.com/search/song), %s' % e)
			self.write(-1)
			return
		if content_from_api is None or len(content_from_api) == 0:
			logger.error('Response data exception (from music.baidu.com/search/song), %s' % e)
			self.write(-1)
			return
		object_from_api = None
		try:
			object_from_api = BeautifulSoup(content_from_api, 'html5lib')
			if object_from_api is None:
				raise Exception('object_from_api is None')
		except Exception, e:
			logger.error('HTML parse failure (from music.baidu.com/search/song), %s' % e)
			self.write(-2)
			return
		res = '{ '
		res += '"result": ['
		song_id_list = []
		search_result_container = object_from_api.select('div[id="result_container"]')
		if search_result_container is not None and len(search_result_container) > 0:
			search_result_container = search_result_container[0]
			data_songitems = search_result_container.select('li[data-songitem]')
			if data_songitems is not None and len(data_songitems) > 0:
				for _ in data_songitems:
					attr_data_songitem = _.get('data-songitem')
					if attr_data_songitem is not None and len(attr_data_songitem) > 0:
						object_data_songitem = None
						try:
							object_data_songitem = json.loads(attr_data_songitem)
						finally:
							pass
						songItem = None
						if object_data_songitem is not None:
							songItem = object_data_songitem.get('songItem')
						sid = None
						if songItem is not None:
							sid = songItem.get('sid')
						if sid is not None:
							song_id_list.append(str(sid))
		song_id_join_str = None
		if len(song_id_list) > 0:
			song_id_join_str = ','.join(song_id_list)
			# songInfo
			content_from_api = None
			try:
				http_client = tornado.httpclient.AsyncHTTPClient()
				response = yield http_client.fetch(BAIDU_SONGINFO_URI % song_id_join_str)
				content_from_api = response.body
			except Exception, e:
				logger.error('HTTP request error (from play.baidu.com/data/music/songInfo, %s' % e)
				self.write(-1)
				return
			if content_from_api is None or len(content_from_api) == 0:
				logger.error('Response data exception (from play.baidu.com/data/music/songInfo')
				self.write(-1)
				return
			object_from_api = None
			try:
				object_from_api = json.loads(content_from_api)
				if object_from_api is None:
					raise Exception('object_from_api is None')
			except Exception, e:
				logger.error('JSON parse failure (from play.baidu.com/data/music/songInfo, %s' % e)
				self.write(-1)
				return
			song_id_name_map = {}
			data = object_from_api.get('data')
			songList = None
			if data is not None:
				songList = data.get('songList')
			if songList is not None and len(songList) > 0:
				for _ in songList:
					songId = _.get('songId')
					songName = _.get('songName')
					artistName = _.get('artistName')
					song_id_name_map[songId] = {
						'songName': songName,
						'artistName': artistName
					}
			# songlink
			content_from_api = None
			try:
				http_client = tornado.httpclient.AsyncHTTPClient()
				response = yield http_client.fetch(BAIDU_SONGLINK_URI % song_id_join_str)
				content_from_api = response.body
			except Exception, e:
				logger.error('HTTP request error (from play.baidu.com/data/music/songlink, %s' % e)
				self.write(-1)
				return
			if content_from_api is None or len(content_from_api) == 0:
				logger.error('Response data exception (from play.baidu.com/data/music/songlink')
				self.write(-1)
				return
			object_from_api = None
			try:
				object_from_api = json.loads(content_from_api)
				if object_from_api is None:
					raise Exception('object_from_api is None')
			except Exception, e:
				logger.error('JSON parse failure (from play.baidu.com/data/music/songlink, %s' % e)
				self.write(-1)
				return
			data = object_from_api.get('data')
			songList = None
			if data is not None:
				songList = data.get('songList')
			if songList is not None and len(songList) > 0:
				song_list_ = []
				for _ in songList:
					songid = _.get('songId')
					songname = ''
					singer = ''
					if songid is not None:
						name_box = song_id_name_map.get(str(songid))
						if name_box is not None:
							songname = name_box.get('songName')
							singer = name_box.get('artistName')
						else:
							songname = _.get('songName')
							singer = _.get('artistName')
					if songname is None:
						#songname = ''
						continue
					if singer is None:
						singer = ''
					album = _.get('albumName')
					if album is None:
						album = ''
					songlink = _.get('songLink')
					if songlink is None:
						#songlink = ''
						continue
					lrclink = _.get('lrcLink')
					if lrclink is not None and len(lrclink) > 0:
						if lrclink.endswith('.lrc'):
							lrclink = 'http://ting.baidu.com' + lrclink
					if lrclink is None:
						lrclink = ''
					time = _.get('time')
					if time is None:
						time = 0
					size = _.get('size')
					if size is None:
						size = 0
					format_ = _.get('format')
					if format_ is None:
						format_ = ''
					song_ = ('{ ' +
						'"songname": "%s", ' % common.strict_str(songname) +
						'"songid": "%s", ' % songid +
						'"singer": "%s", ' % common.strict_str(singer) +
						'"album": "%s", ' % common.strict_str(album) +
						'"songlink": "%s", ' % songlink +
						'"lrclink": "%s", ' % lrclink +
						'"time": %s, ' % time +
						'"size": %s, ' % size +
						'"format": "%s"' % format_ +
						' }')
					song_list_.append(song_)
				song_list_str = ','.join(song_list_)
				res += song_list_str
		res += ']'
		res += ' }'
		MusicSearchHandler.song_name_result_map[song_name] = {
			'res': res,
			'time': datetime.datetime.now()
		}
		if config.Mode == 'DEBUG' and pretty_state is not None and pretty_state:
			res = common.pretty_print(res)
		self.write(res)


	def write(self, trunk):
		if type(trunk) == int:
			trunk = str(trunk)
		super(MusicSearchHandler, self).write(trunk)
