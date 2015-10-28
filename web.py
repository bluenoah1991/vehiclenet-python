#!/usr/bin/python

import sys, os
import tornado.ioloop
import tornado.web
import logging
import logging.handlers
import re

import vehiclenet.weather

reload(sys)
sys.setdefaultencoding('utf8')

def deamon(chdir = False):
	try:
		if os.fork() > 0:
			os._exit(0)
	except OSError, e:
		print 'fork #1 failed: %d (%s)' % (e.errno, e.strerror)
		os._exit(1)

def init():
	vehiclenet.weather.WeatherHandler.cache()

class DefaultHandler(tornado.web.RequestHandler):
	def get(self):
		self.write('VehicleNet Say Hello!')

settings = {
	"static_path": os.path.join(os.path.dirname(__file__), "static"),
}

application = tornado.web.Application([
	(r"/", DefaultHandler),
	(r"/carlink/weather/findWeather.htm", vehiclenet.weather.WeatherHandler),
], **settings)

if __name__ == "__main__":
	if '-d' in sys.argv:
		deamon()
	logdir = 'logs'
	if not os.path.exists(logdir):
		os.makedirs(logdir)
	fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'
	formatter = logging.Formatter(fmt)
	handler = logging.handlers.TimedRotatingFileHandler(
		'%s/logging' % logdir, 'M', 20, 360)
	handler.suffix = '%Y%m%d%H%M%S.log'
	handler.extMatch = re.compile(r'^\d{4}\d{2}\d{2}\d{2}\d{2}\d{2}')
	handler.setFormatter(formatter)
	logger = logging.getLogger('web')
	logger.addHandler(handler)
	logger.setLevel(logging.DEBUG)

	init()

	application.listen(80)
	print 'Server is running, listening on port 80....'
	tornado.ioloop.IOLoop.instance().start()
