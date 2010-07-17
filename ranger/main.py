# -*- coding: utf-8 -*-
# Copyright (C) 2009, 2010  Roman Zimbelmann <romanz@lavabit.com>
# This program is free software; see COPYING for details.
from ranger.status import Status
from ranger.gui import ui
from ranger.fs import File, Directory, npath
from ranger.ext.shell_escape import shell_escape
from ranger.communicate import data_dir
import os
import sys
import curses
import locale

def main():
	try: locale.setlocale(locale.LC_ALL, '')
	except: print("Warning: Unable to set locale.  Expect encoding problems.")
	global status
	status = Status()
	File.status = status
	settingsfile = os.sep.join([data_dir(), 'settings.py'])
	settings = compile(open(settingsfile).read(), settingsfile, 'exec')
	exec(settings, globals())
	origin = npath(sys.argv[1], '.') if len(sys.argv) > 1 else os.getcwd()
	status.origin = origin
	status.change_cwd(origin)
	try:
		status.stdscr = curses.initscr()
		load_status(status)
		status.curses_on()
		ui(status)
	except KeyboardInterrupt:
		pass
	finally:
		status.curses_off()
		save_status(status)


def load_status(status):
	try:
		pointer = os.environ['RANGER_POINTER']
	except:
		pass
	else:
		dir = status.get_dir(os.path.dirname(pointer))
		dir.select_filename(pointer)
	status.sync_pointer()


def save_status(status):
	from ranger.communicate import echo
	try:
		echo(status.cwd.path, 'last_dir')
		echo(status.cwd.current_file.path, 'last_pointer')
		echo(str(status.cwd.scroll_begin), 'last_scroll_start')
		echo('\n'.join(status.selection), 'last_selection')
	except:
		pass
