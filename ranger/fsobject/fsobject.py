# Copyright (c) 2009, 2010 hut <hut@lavabit.com>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

CONTAINER_EXTENSIONS = 'rar zip tar gz bz bz2 tgz 7z iso cab'.split()
DOCUMENT_EXTENSIONS = 'pdf doc ppt odt'.split()
DOCUMENT_BASENAMES = 'README TODO LICENSE COPYING INSTALL'.split()

from . import T_FILE, T_DIRECTORY, T_UNKNOWN, T_NONEXISTANT, BAD_INFO
from ranger.shared import MimeTypeAware, FileManagerAware
from ranger.ext.shell_escape import shell_escape2

class FileSystemObject(MimeTypeAware, FileManagerAware):
	is_file = False
	is_directory = False
	content_loaded = False
	force_load = False
	path = None
	basename = None
	basename_lower = None
	_shell_escaped_basename = None
	dirname = None
	extension = None
	exists = False
	accessible = False
	marked = False
	tagged = False
	loaded = False
	runnable = False
	islink = False
	readlink = None
	stat = None
	infostring = None
	permissions = None
	type = T_UNKNOWN
	size = 0

	last_used = None

	stopped = False

	video = False
	image = False
	audio = False
	media = False
	document = False
	container = False
	mimetype_tuple = ()

	def __init__(self, path):
		MimeTypeAware.__init__(self)
		if type(self) == FileSystemObject:
			raise TypeError("Cannot initialize abstract class FileSystemObject")

		from os.path import abspath, basename, dirname, realpath

		path = abspath(path)
		self.path = path
		self.basename = basename(path)
		self.basename_lower = self.basename.lower()
		self.dirname = dirname(path)
		self.realpath = realpath(path)

		try:
			self.extension = self.basename[self.basename.rindex('.') + 1:].lower()
		except ValueError:
			self.extension = None

		self.set_mimetype()
		self.use()

	@property
	def shell_escaped_basename(self):
		if self._shell_escaped_basename is None:
			self._shell_escaped_basename = shell_escape2(self.basename)
		return self._shell_escaped_basename

	def get_description(self):
		return "Loading " + str(self)

	def __str__(self):
		"""returns a string containing the absolute path"""
		return str(self.path)

	def use(self):
		"""mark the filesystem-object as used at the current time"""
		import time
		self.last_used = time.time()

	def is_older_than(self, seconds):
		"""returns whether this object wasn't use()d in the last n seconds"""
		import time
		return self.last_used + seconds < time.time()

	def set_mimetype(self):
		"""assign attributes such as self.video according to the mimetype"""
		try:
			self.mimetype = self.mimetypes[self.extension]
		except KeyError:
			self.mimetype = ''

		self.video = self.mimetype.startswith('video')
		self.image = self.mimetype.startswith('image')
		self.audio = self.mimetype.startswith('audio')
		self.media = self.video or self.image or self.audio
		self.document = self.mimetype.startswith('text') or (self.extension in DOCUMENT_EXTENSIONS) or (self.basename in DOCUMENT_BASENAMES)
		self.container = self.extension in CONTAINER_EXTENSIONS

		keys = ('video', 'audio', 'image', 'media', 'document', 'container')
		self.mimetype_tuple = tuple(key for key in keys if getattr(self, key))

		if self.mimetype == '':
			self.mimetype = None

	def mark(self, boolean):
		directory = self.env.get_directory(self.dirname)
		directory.mark_item(self)

	def _mark(self, boolean):
		"""Called by directory.mark_item() and similar functions"""
		self.marked = bool(boolean)

	def load(self):
		"""
		reads useful information about the filesystem-object from the
		filesystem and caches it for later use
		"""
		import os
		import stat
		from ranger.ext.human_readable import human_readable

		self.loaded = True

		try:
			self.stat = os.lstat(self.path)
		except OSError:
			self.stat = None
			self.islink = False
			self.accessible = False
		else:
			self.islink = stat.S_ISLNK(self.stat.st_mode)
			self.accessible = True

		if os.access(self.path, os.F_OK):
			self.exists = True
			self.accessible = True

			if os.path.isdir(self.path):
				self.type = T_DIRECTORY
				try:
					self.size = len(os.listdir(self.path))
					self.infostring = ' %d' % self.size
					self.runnable = True
				except OSError:
					self.infostring = BAD_INFO
					self.runnable = False
					self.accessible = False
			elif os.path.isfile(self.path):
				self.type = T_FILE
				self.size = self.stat.st_size
				self.infostring = ' ' + human_readable(self.stat.st_size)
			else:
				self.type = T_UNKNOWN
				self.infostring = None

		else:
			if self.islink:
				self.infostring = '->'
			else:
				self.infostring = None
			self.type = T_NONEXISTANT
			self.exists = False
			self.runnable = False

		if self.islink:
			self.readlink = os.readlink(self.path)

	def get_permission_string(self):
		if self.permissions is not None:
			return self.permissions

		if self.accessible is False:
			return '----------'

		import stat
		mode = self.stat.st_mode

		if stat.S_ISDIR(mode):
			perms = ['d']
		elif stat.S_ISLNK(mode):
			perms = ['l']
		else:
			perms = ['-']

		for who in "USR", "GRP", "OTH":
			for what in "rwx":
				if mode & getattr(stat, "S_I" + what.upper() + who):
					perms.append( what.lower() )
				else:
					perms.append( '-' )

		self.permissions = ''.join(perms)
		return self.permissions

	def load_once(self):
		"""calls load() if it has not been called at least once yet"""
		if not self.loaded:
			self.load()
			return True
		return False

	def go(self):
		"""enter the directory if the filemanager is running"""
		if self.fm:
			return self.fm.enter_dir(self.path)
		return False

	def load_if_outdated(self):
		"""
		Calls load() if the currently cached information is outdated
		or nonexistant.
		"""
		if self.load_once(): return True

		import os
		try:
			real_mtime = os.lstat(self.path).st_mtime
		except OSError:
			real_mtime = None
		if self.stat:
			cached_mtime = self.stat.st_mtime
		else:
			cached_mtime = 0

		if real_mtime != cached_mtime:
			self.load()
			return True
		return False
