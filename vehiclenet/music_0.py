#!/usr/bin/python

import sys, os, threading
import tornado.web
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

BAIDU_TOP_URI = 'http://music.baidu.com/top/new/week'
BAIDU_SONGLINK_URI = 'http://play.baidu.com/data/music/songlink?songIds=%s'
BAIDU_SONGINFO_URI = 'http://play.baidu.com/data/music/songInfo?songIds=%s'

logger = logging.getLogger('web')

interval = datetime.timedelta(minutes=59)

class MusicTopHandler(tornado.web.RequestHandler):

	music_top_cache = {} # TODO persistence

	music_top_cache_expire_time = datetime.datetime.min

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

		if datetime.datetime.now() < MusicTopHandler.music_top_cache_expire_time + interval:
			res_ = MusicTopHandler.music_top_cache
			if config.Mode == 'DEBUG' and pretty_state is not None and pretty_state:
				res_ = common.pretty_print(res_)
			self.write(res_)
			return
		content_from_api = None
		try:
			response = urllib2.urlopen(BAIDU_TOP_URI)
			content_from_api = response.read()
			response.close()
		except Exception, e:
			logger.error('HTTP request error (from music.baidu.com/top/new/week), %s' % e)
			self.write(-1)
			return
		if content_from_api is None or len(content_from_api) == 0:
			logger.error('Response data exception (from music.baidu.com/top/new/week), %s' % e)
			self.write(-1)
			return
		object_from_api = None
		try:
			object_from_api = BeautifulSoup(content_from_api, 'html5lib')
			if object_from_api is None:
				raise Exception('object_from_api is None')
		except Exception, e:
			logger.error('HTML parse failure (from music.baidu.com/top/new/week), %s' % e)
			self.write(-2)
			return
		res = '{ '
		res += '"result": ['
		song_id_list = []
		new_week_song_list_wrapper = object_from_api.select('div[id="newWeekSongListWrapper"]')
		if new_week_song_list_wrapper is not None and len(new_week_song_list_wrapper) > 0:
			new_week_song_list_wrapper = new_week_song_list_wrapper[0]
			data_songitems = new_week_song_list_wrapper.select('li[data-songitem]')
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
							if len(song_id_list) >= 11:
								break
		song_id_join_str = None
		if len(song_id_list) > 0:
			song_id_join_str = ','.join(song_id_list)
			# songInfo
			content_from_api = None
			try:
				response = urllib2.urlopen(BAIDU_SONGINFO_URI % song_id_join_str)
				content_from_api = response.read()
				response.close()
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
				response = urllib2.urlopen(BAIDU_SONGLINK_URI % song_id_join_str)
				content_from_api = response.read()
				response.close()
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
					songname = None
					singer = None
					if songid is not None:
						name_box = song_id_name_map.get(str(songid))
						if name_box is not None:
							songname = name_box.get('songName')
							singer = name_box.get('artistName')
						else:
							songname = _.get('songName')
							singer = _.get('artistName')
					album = _.get('albumName')
					songlink = _.get('songLink')
					lrclink = _.get('lrcLink')
					if lrclink is not None and len(lrclink) > 0:
						if lrclink.endswith('.lrc'):
							lrclink = 'http://ting.baidu.com' + lrclink
					time = _.get('time')
					size = _.get('size')
					format_ = _.get('format')
					song_ = ('{ ' +
						'"songname": "%s", ' % songname +
						'"songid": "%s", ' % songid +
						'"singer": "%s", ' % singer +
						'"album": "%s", ' % album +
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
		MusicTopHandler.music_top_cache = res
		MusicTopHandler.music_top_cache_expire_time = datetime.datetime.now()
		if config.Mode == 'DEBUG' and pretty_state is not None and pretty_state:
			res = common.pretty_print(res)
		self.write(res)


	def write(self, trunk):
		if type(trunk) == int:
			trunk = str(trunk)
		super(MusicTopHandler, self).write(trunk)
