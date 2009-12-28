from os.path import abspath, normpath, join, expanduser, isdir
import os
from ranger.fsobject.directory import Directory, NoDirectoryGiven
from ranger.container import KeyBuffer, History
from ranger.shared import SettingsAware

class Environment(SettingsAware):
	"""A collection of data which is relevant for more than
	one class.
	"""

	pwd = None  # current directory
	cf = None  # current file
	copy = None
	cut = None
	termsize = None
	history = None
	directories = None
	last_search = None
	pathway = None
	path = None
	keybuffer = None

	def __init__(self, path):
		self.path = abspath(expanduser(path))
		self.pathway = ()
		self.directories = {}
		self.keybuffer = KeyBuffer()
		self.copy = set()
		self.history = History(self.settings.max_history_size)

		from ranger.shared import EnvironmentAware
		EnvironmentAware.env = self

	def key_append(self, key):
		"""Append a key to the keybuffer"""
		from ranger import log
		self.keybuffer.append(key)

	def key_clear(self):
		"""Clear the keybuffer"""
		self.keybuffer.clear()
	
	def at_level(self, level):
		"""Returns the FileSystemObject at the given level.
		level 1 => preview
		level 0 => current file/directory
		level <0 => parent directories"""
		if level <= 0:
			try:
				return self.pathway[level - 1]
			except IndexError:
				return None
		else:
			try:
				return self.directories[self.cf.path]
			except AttributeError:
				return None
			except KeyError:
				return self.cf

	def garbage_collect(self):
		"""Delete unused directory objects"""
		from ranger.fsobject.fsobject import FileSystemObject
		for key in tuple(self.directories.keys()):
			value = self.directories[key]
			if isinstance(value, FileSystemObject):
				if value.is_older_than(1200):
					del self.directories[key]
	
	def get_selection(self):
		if self.pwd:
			return self.pwd.get_selection()
		return set()
	
	def get_directory(self, path):
		"""Get the directory object at the given path"""
		path = abspath(path)
		try:
			return self.directories[path]
		except KeyError:
			obj = Directory(path)
			self.directories[path] = obj
			return obj

	def assign_correct_cursor_positions(self):
		"""Assign correct cursor positions for subdirectories"""
		last_path = None
		for path in reversed(self.pathway):
			if last_path is None:
				last_path = path
				continue

			path.move_to_obj(last_path)
			last_path = path
	
	def history_go(self, relative):
		"""Move relative in history"""
		if self.history:
#			self.enter_dir(self.history.move(relative))
			self.history.move(relative).go()

	def enter_dir(self, path, history = True):
		"""Enter given path"""
		if path is None: return
		path = str(path)

		# get the absolute path
		path = normpath(join(self.path, expanduser(path)))

		if not isdir(path):
			return

		try:
			new_pwd = self.get_directory(path)
		except NoDirectoryGiven:
			return False

		self.path = path
		self.pwd = new_pwd
		os.chdir(path)

		self.pwd.load_content_if_outdated()

		# build the pathway, a tuple of directory objects which lie
		# on the path to the current directory.
		if path == '/':
			self.pathway = (self.get_directory('/'), )
		else:
			pathway = []
			currentpath = '/'
			for dir in path.split('/'):
				currentpath = join(currentpath, dir)
				pathway.append(self.get_directory(currentpath))
			self.pathway = tuple(pathway)

		self.assign_correct_cursor_positions()

		# set the current file.
		self.pwd.directories_first = self.settings.directories_first
		self.pwd.sort_if_outdated()
		self.cf = self.pwd.pointed_obj

		if history:
			self.history.add(new_pwd)

		return True
