# -*- coding: utf-8 -*-
# Copyright (C) 2009, 2010  Roman Zimbelmann <romanz@lavabit.com>
# This software is licensed under the GNU GPLv3; see COPYING for details.
"""
This file is responsible for drawing the UI
"""

import curses
import _curses
import socket
from pithy.ext.human_readable import human_readable
from pithy.ext.color import *
from pwd import getpwuid
from grp import getgrgid
from os import getuid, readlink, geteuid
from time import time, strftime, localtime

OTHERWISE = None

def clr(fg, bg):
	return curses.color_pair(get_color(fg, bg))

class Context(object):
	selected = False

class Bounds(object):
	def __init__(self, **kw):
		self.__dict__ = kw

def ui(status):
	win = status.stdscr
	username, hostname = status.username, status.hostname

	def safechgat(*args):
		try: win.chgat(*args)
		except _curses.error: pass

	def safeaddnstr(*args):
		try: win.addnstr(*args)
		except _curses.error: pass

	def draw_row(level, directory, bounds, info=False):
		b = bounds
		if directory.files is None:
			return
		for i in range(len(directory.files)):
			y = i + b.y
			actual_i = i + directory.scroll_begin
			if y >= b.y + b.hei:
				break
			try:
				f = directory.files[actual_i]
			except:
				break
			basename = f.basename
			if status.classify and f.classification:
				basename += f.classification
			if info:
				safeaddnstr(y, b.x, "%s%3d %s %s %6s %s %s" % (
					f.permission_string, f.stat.st_nlink,
					getpwuid(f.stat.st_uid)[0],
					getgrgid(f.stat.st_gid)[0],
					human_readable(f.stat.st_size),
					strftime('%b %d %H:%M', localtime(f.stat.st_mtime)),
					basename), b.wid)
			else:
				fname = status.hooks.filename(basename, f, level, b.wid)
				if isinstance(fname, tuple):
					safeaddnstr(y, b.x, fname[0], b.wid)
					safeaddnstr(y, b.x + b.wid - len(fname[1]), fname[1], -1)
				else:
					safeaddnstr(y, b.x, fname, b.wid)
			is_selected = (actual_i == directory.pointer)
			context = Context()
			context.selected = is_selected
			fg, bg, attr = status.hooks.get_color(f, context)
			safechgat(y, b.x, b.wid, attr | clr(fg, bg))

	def draw():
		# draw ui
		win.erase()

		# titlebar
		start = username + '@' + hostname + ':'
		mid = start + status.cwd.path
		safeaddnstr(0, 0, mid + (cf and '/' + cf.basename or '/'), wid)
		safechgat(0, 0, -1, bold | clr(blue, -1))
		safechgat(0, 0, len(start), bold | clr(green, -1))
		safechgat(0, len(mid), -1, bold | clr(white, -1))

		# statusbar
		y = hei - 1
		statushook = status.hooks.statusbar()
		if statushook is not None:
			safeaddnstr(y, 0, statushook, wid)
		elif cf:
			perms = cf.permission_string
			safeaddnstr(y, 0, cf.permission_string, -1)
			color = clr(cyan if getuid() == cf.stat.st_uid else magenta, -1)
			safechgat(y, 0, 10, color)
			if cf.is_link:
				try:    lastinfo = ' -> ' + readlink(cf.path)
				except: lastinfo = ' -> ?'
			else:
				lastinfo = strftime('%Y-%m-%d %H:%M',
						localtime(cf.stat.st_mtime))
			try:
				user = getpwuid(cf.stat.st_uid)[0]
			except KeyError:
				user = str(cf.stat.st_uid)
			try:
				group = getgrgid(cf.stat.st_gid)[0]
			except KeyError:
				group = str(cf.stat.st_gid)
			info = ' '.join([str(cf.stat.st_nlink), user, group, lastinfo])
			safeaddnstr(y, 11, info, -1)
		if cf:
			scroll_start = cwd.scroll_begin
			max_pos = len(cwd.files) - hei - 2
			if max_pos < 0:
				shown = 'All'
			elif scroll_start == 0:
				shown = 'Top'
			elif scroll_start >= max_pos:
				shown = 'Bot'
			else:
				shown = '{0:0>.0f}%'.format(100.0 * scroll_start / max_pos)
			pos = str(cwd.pointer + 1) + '/' + str(len(cwd.files))

			right = '  '.join((pos, shown))
			safeaddnstr(y, wid - len(right), right, len(right))
		else:
			right = "0/0  All"
			safeaddnstr(y, wid - len(right), right, len(right))

		if status.ls_l_mode:
			draw_row(0, cwd, Bounds(x=0, y=1, wid=wid, hei=hei-2), info=True)

		else:
			# columns
			rows = status.rows
			if cf and not cf.is_dir and rows[-1][0] == 1:
				cut_off = sum(row[1] for row in rows if row[0] > 0)
				rows = [row for row in rows if row[0] <= 0]
				rows[-1] = [rows[-1][0], rows[-1][1] + cut_off]
			ratiosum = float(sum(row[1] for row in rows))
			lastx = 0
			for i, row in enumerate(rows):
				level, ratio = row
				directory = status.get_level(level)
				rowwid = int(ratio / ratiosum * wid)
				if directory:
					draw_row(level, directory,
							Bounds(x=lastx,y=1,wid=rowwid,hei=hei-2))
				lastx += rowwid + 1

	while True:
		hei, wid = win.getmaxyx()
		cwd = status.cwd
		cf = cwd.current_file

		# -------------------------
		draw()

		# -------------------------
		# handle input
		c = win.getch()
		status.lastkey = c
		if c == curses.KEY_RESIZE:
			status.move(status.cwd.pointer)
		else:
			try: action = status.keymap[c]
			except:
				try: action = status.keymap[OTHERWISE]
				except: continue
			try:
				action()
			except TypeError:
				action(status)
