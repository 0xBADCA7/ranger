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

class Accumulator(object):
	def __init__(self):
		self.pointer = 0
		self.pointed_obj = None

	def move(self, relative=0, absolute=None, pages=None, narg=None):
		i = self.pointer
		lst = self.get_list()
		if not lst:
			return self.pointer
		length = len(lst)

		if isinstance(absolute, int):
			if isinstance(narg, int):
				absolute = narg
			if absolute < 0: # wrap
				i = absolute + length
			else:
				i = absolute

		if relative != 0:
			if isinstance(pages, int):
				relative *= pages * self.get_height()
			if isinstance(narg, int):
				relative *= narg
		i = int(i + relative)

		if i >= length:
			i = length - 1
		if i < 0:
			i = 0

		self.pointer = i
		self.correct_pointer()
		return self.pointer

	def move_to_obj(self, arg, attr=None):
		if not arg:
			return

		lst = self.get_list()

		if not lst:
			return

		do_get_attr = isinstance(attr, str)

		good = arg
		if do_get_attr:
			try:
				good = getattr(arg, attr)
			except (TypeError, AttributeError):
				pass

		for obj, i in zip(lst, range(len(lst))):
			if do_get_attr:
				try:
					test = getattr(obj, attr)
				except AttributeError:
					continue
			else:
				test = obj

			if test == good:
				self.move(absolute=i)
				return True

		return self.move(absolute=self.pointer)

	def correct_pointer(self):
		lst = self.get_list()

		if not lst:
			self.pointer = 0
			self.pointed_obj = None

		else:
			i = self.pointer

			if i is None:
				i = 0
			if i >= len(lst):
				i = len(lst) - 1
			if i < 0:
				i = 0

			self.pointer = i
			self.pointed_obj = lst[i]

	def pointer_is_synced(self):
		lst = self.get_list()
		try:
			return lst[self.pointer] == self.pointed_obj
		except (IndexError, KeyError):
			return False

	def sync_index(self, **kw):
		self.move_to_obj(self.pointed_obj, **kw)

	def get_list(self):
		"""OVERRIDE THIS"""
		return []

	def get_height(self):
		"""OVERRIDE THIS"""
		return 25
