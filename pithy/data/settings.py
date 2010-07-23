# -*- coding: utf-8 -*-
# Copyright (C) 2009, 2010  Roman Zimbelmann <romanz@lavabit.com>
# This software is licensed under the GNU GPLv3; see COPYING for details.

import stat
import os
from pithy.gui import OTHERWISE
from pithy.ext.color import *
from pithy.ext.human_readable import human_readable
from pithy.ext.fast_typetest import *
from curses.ascii import ctrl
import pithy

# ------------------------------------------------------------------
# Define variables
# ------------------------------------------------------------------
# status is a global variable set by pithy.  Abbreviate it with s:
s = status

ALLOWED_BOOKMARKS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
		"abcdefghijklmnopqrstuvwxyz0123456789`'")

keybuffer = None
info_strings = {}
show_number_of_files_in_directories = False

# ------------------------------------------------------------------
# Set hooks
# ------------------------------------------------------------------
HIDE_EXTENSIONS = '~', 'bak', 'pyc', 'pyo', 'srt', 'swp'

def hook(fnc):
	setattr(status.hooks, fnc.__name__, fnc)  # override a hook

def hide_files(filename, path):
	if filename[0] == '.':
		return False
	if any(filename.endswith(ext) for ext in HIDE_EXTENSIONS):
		return False
	return filename != 'lost+found'
status.hooks.filter = hide_files

@hook
def statusbar():
	if keybuffer is not None:
		return "find: " + keybuffer
	return None

# how should the filename be displayed?
@hook
def filename(basename, fileobj, level, width):
	if level != 0:
		return basename
	try:
		return (basename, info_strings[fileobj])
	except KeyError:
		if show_number_of_files_in_directories and fileobj.is_dir:
			try:
				info_string = str(len(os.listdir(fileobj.path)))
			except:
				info_string = "?"
		else:
			info_string = human_readable(fileobj.stat.st_size)
		# let's cache the result for faster access
		info_strings[fileobj] = info_string
		return (basename, info_string)

@hook
def reload_hook():
	# clear the cache of the filename-hook
	info_strings.clear()

@hook
def get_color(f, context):
	fg, bg, attr = default, default, normal
	ext = f.extension.lower()
	if context.selected:
		attr = reverse
	if f.is_dir:
		fg = blue
		attr |= bold
	elif is_image(ext):
		fg = yellow
	elif is_video(ext) or is_audio(ext):
		fg = magenta
	elif is_container(ext):
		fg = red
	elif stat.S_ISCHR(f.stat.st_mode) or stat.S_ISBLK(f.stat.st_mode):
		fg = yellow
		attr |= bold
	elif stat.S_ISSOCK(f.stat.st_mode):
		fg = magenta
		attr |= bold
	elif stat.S_ISFIFO(f.stat.st_mode):
		fg = yellow
	elif f.stat.st_mode & stat.S_IXUSR:
		fg = green
		attr |= bold
	if f.is_link:
		fg = cyan
	if f.path in status.selection:
		fg = yellow
		attr |= bold
	return fg, bg, attr

# ------------------------------------------------------------------
# Define the keymap and functions used in the keymap
# ------------------------------------------------------------------
def break_keychain():
	global keybuffer
	keybuffer = None
	status.keymap = keys

def show_files(filename, path):
	return True

def toggle_hidden():
	s.hooks.filter = show_files if s.hooks.filter == hide_files else hide_files
	s.reload()

def enter_dir_or_run_file():
	cf = s.cwd.current_file
	if cf:
		if cf.is_dir:
			return s.cd(cf.path)
		status.launch('rifle.py %f')

def set_sort_mode(fnc):
	def function():
		if status.sort_key != fnc:
			status.sort_key = fnc
			status.reload()
	return function

def goto_newest_file():
	best = max(status.cwd.files, key=lambda f: f.stat.st_size)
	status.cwd.select_filename(best.path)
	status.sync_pointer()

keys_raw = {
	'r': lambda: s.reload(),
	'j': lambda: s.move(s.cwd.pointer + 1),
	'k': lambda: s.move(s.cwd.pointer - 1),
	'd': lambda: s.move(s.cwd.pointer + 20),
	'u': lambda: s.move(s.cwd.pointer - 20),
	'h': lambda: s.cd('..'),
	'l': enter_dir_or_run_file,
	'c': goto_newest_file,
	'E': lambda: s.launch('vim %f'),
	'i': lambda: s.launch('(highlight --ansi %f 2> /dev/null || cat %f) | less -R'),
	'G': lambda: s.move(len(s.cwd.files) - 1),
	'w': lambda: setattr(s, 'ls_l_mode', not s.ls_l_mode),
	'g': lambda: setattr(s, 'keymap', g_keys),
	'm': lambda: (setattr(s, 'draw_bookmarks', True),
	              setattr(s, 'keymap', set_bookmark_handler)),
	'`': lambda: (setattr(s, 'draw_bookmarks', True),
	              setattr(s, 'keymap', go_bookmark_handler)),
	'x': lambda: setattr(s, 'keymap', custom_keys),
	'f': lambda: (setattr(s, 'keymap', find_keys),
	              globals().__setitem__('keybuffer', '')),
	'1': set_sort_mode(None),
	'2': set_sort_mode(lambda f: -f.stat.st_size),
	'3': set_sort_mode(lambda f: -f.stat.st_mtime),
	'q': lambda: s.exit(),
	' ': lambda: (s.toggle_select_file(s.cwd.current_file.path),
	              s.move(s.cwd.pointer + 1)),
	ctrl('h'): toggle_hidden,
}

# define some aliases:
keys_raw["'"] = keys_raw["`"]
keys_raw["Q"] = keys_raw["q"]
keys_raw["s"] = keys_raw["Q"]
keys_raw["J"] = keys_raw["d"]
keys_raw["K"] = keys_raw["u"]
keys_raw["/"] = keys_raw["f"]

g_keys_raw = {
	'g': lambda: s.move(0),
	'0': lambda: s.cd(s.origin),
	OTHERWISE: lambda: None  # this breaks key chain
}

def cd(path):
	return lambda: status.cd(path)

for key, path in {
	'h': '~', 'u': '/usr', 'r': '/', 'm': '/media', 't': '/tmp',
}.items(): g_keys_raw[key] = cd(path)

custom_keys_raw = {
	'u': lambda: status.launch('du -h --apparent-size --max-depth=1 | less'),
	'f': lambda: status.launch('df -h | less'),
	OTHERWISE: lambda: None  # this breaks key chain
}

def _bookmark_key():
	break_keychain()
	status.draw_bookmarks = False
	try:
		key = chr(status.lastkey)
		assert key in ALLOWED_BOOKMARKS
	except:
		return
	if key == '`':
		key = "'"
	return key

def set_bookmark():
	status.set_bookmark(_bookmark_key(), status.cwd.path)

def go_bookmark():
	status.enter_bookmark(_bookmark_key())

go_bookmark_handler   = { OTHERWISE: go_bookmark }
set_bookmark_handler  = { OTHERWISE: set_bookmark }

def find_mode():
	global keybuffer
	try:
		chr_lastkey = chr(status.lastkey)
	except:
		if status.lastkey == curses.KEY_BACKSPACE:
			find_mode_backspace()
	else:
		if chr_lastkey == 127:
			find_mode_backspace()
		else:
			keybuffer += chr(status.lastkey)
	if keybuffer is None:
		return
	count = 0
	for f in status.cwd.files:
		if keybuffer in f.basename.lower():
			count += 1
			if count == 1:
				status.cwd.select_filename(f.path)
				status.sync_pointer()
	if count <= 1:
		break_keychain()
		if count == 1:
			cf = status.cwd.current_file
			if cf.is_dir:
				status.cd(cf.path)

def find_mode_backspace():
	global keybuffer
	keybuffer = keybuffer[:-1]
	if not keybuffer:
		break_keychain()

find_keys = { OTHERWISE: find_mode }

def break_keychain_wrap(fnc):
	def wrap():
		break_keychain()
		return fnc()
	return wrap

def normalize_key(c):
	try:
		return ord(c)
	except:
		return c

g_keys = dict((normalize_key(c), break_keychain_wrap(fnc)) \
		for c, fnc in g_keys_raw.items())
custom_keys = dict((normalize_key(c), break_keychain_wrap(fnc)) \
		for c, fnc in custom_keys_raw.items())
keys = dict((normalize_key(c), fnc) for c, fnc in keys_raw.items())
status.keymap = keys
