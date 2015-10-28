#!/usr/bin/python

import sys, os

def get_file_from_current_dir(_file_, filename):
	path = os.path.split(os.path.realpath(_file_))[0]
	return os.path.join(path, filename)
