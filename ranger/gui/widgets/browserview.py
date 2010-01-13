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

"""The BrowserView manages a set of BrowserColumns."""
from . import Widget
from .browsercolumn import BrowserColumn
from .pager import Pager
from ..displayable import DisplayableContainer

class BrowserView(Widget, DisplayableContainer):
	ratios = None
	preview = True
	preview_available = True
	stretch_ratios = None
	need_clear = False

	def __init__(self, win, ratios, preview = True):
		DisplayableContainer.__init__(self, win)
		self.ratios = ratios
		self.preview = preview

		# normalize ratios:
		ratio_sum = float(sum(ratios))
		self.ratios = tuple(map(lambda x: x / ratio_sum, ratios))

		if len(self.ratios) >= 2:
			self.stretch_ratios = self.ratios[:-2] + \
					((self.ratios[-2] + self.ratios[-1] * 0.9),
					(self.ratios[-1] * 0.1))
		
		offset = 1 - len(ratios)
		if preview: offset += 1

		for level in range(len(ratios)):
			fl = BrowserColumn(self.win, level + offset)
			self.add_child(fl)

		try:
			self.main_column = self.container[preview and -2 or -1]
		except IndexError:
			self.main_column = None
		else:
			self.main_column.display_infostring = True
			self.main_column.main_column = True

		self.pager = Pager(self.win, embedded=True)
		self.pager.visible = False
		self.add_child(self.pager)

	def draw(self):
		if str(self.env.keybuffer) in ("`", "'"):
			self._draw_bookmarks()
		else:
			if self.need_clear:
				self.win.erase()
				self.need_redraw = True
				self.need_clear = False
			DisplayableContainer.draw(self)
	
	def _draw_bookmarks(self):
		self.need_clear = True

		sorted_bookmarks = sorted(item for item in self.fm.bookmarks \
				if item[0] != '`' and '/.' not in item[1].path)

		def generator():
			return zip(range(self.hei), sorted_bookmarks)

		try:
			maxlen = max(len(item[1].path) for i, item in generator())
		except ValueError:
			return
		maxlen = min(maxlen + 5, self.wid)

		for line, items in generator():
			key, mark = items
			string = " " + key + ": " + mark.path
			self.addnstr(line, 0, string.ljust(maxlen), self.wid)
	
	def resize(self, y, x, hei, wid):
		"""Resize all the columns according to the given ratio"""
		DisplayableContainer.resize(self, y, x, hei, wid)
		left = 0

		cut_off_last = self.preview and not self.preview_available \
				and self.stretch_ratios

		if cut_off_last:
			generator = zip(self.stretch_ratios, range(len(self.ratios)))
		else:
			generator = zip(self.ratios, range(len(self.ratios)))

		last_i = len(self.ratios) - 1

		for ratio, i in generator:
			wid = int(ratio * self.wid)

			if i == last_i:
				wid = int(self.wid - left + 1)

			if i == last_i - 1:
				self.pager.resize(0, left, hei, max(1, self.wid - left))

			try:
				self.container[i].resize(0, left, hei, max(1, wid-1))
			except KeyError:
				pass

			left += wid
	
	def click(self, event):
		n = event.ctrl() and 1 or 3
		if event.pressed(4):
			self.main_column.scroll(relative = -n)
		elif event.pressed(2) or event.key_invalid():
			self.main_column.scroll(relative = n)
		else:
			DisplayableContainer.click(self, event)
	
	def open_pager(self):
		self.pager.visible = True
		self.pager.focused = True
		self.pager.open()
		try:
			self.container[-2].visible = False
			self.container[-3].visible = False
		except IndexError:
			pass
	
	def close_pager(self):
		self.pager.visible = False
		self.pager.focused = False
		self.pager.close()
		try:
			self.container[-2].visible = True
			self.container[-3].visible = True
		except IndexError:
			pass
	
	def poke(self):
		DisplayableContainer.poke(self)
		if self.settings.collapse_preview and self.preview:
			has_preview = self.container[-2].has_preview()
			if self.preview_available != has_preview:
				self.preview_available = has_preview
				self.resize(self.y, self.x, self.hei, self.wid)
