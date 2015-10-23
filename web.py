#!/usr/bin/python

import sys, os
import tornado.ioloop
import tornado.web

reload(sys)
sys.setdefaultencoding('utf8')

def deamon(chdir = False):
	try:
		if os.fork() > 0:
			os._exit(0)
	except OSError, e:
		print 'fork #1 failed: %d (%s)' % (e.errno, e.strerror)
		os._exit(1)

class DefaultHandler(tornado.web.RequestHandler):
	def get(self):
		self.write('VehicleNet Say Hello!')

settings = {
	"static_path": os.path.join(os.path.dirname(__file__), "static"),
}

application = tornado.web.Application([
	(r"/", DefaultHandler),
], **settings)

if __name__ == "__main__":
	if '-d' in sys.argv:
		deamon()
	application.listen(80)
	print 'Server is running, listening on port 80....'
	tornado.ioloop.IOLoop.instance().start()
