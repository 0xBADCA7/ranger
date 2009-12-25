"""The TitleBar widget displays the current path and some other useful
information."""

from . import Widget
from ranger import log
from math import floor

class TitleBar(Widget):
	old_cf = None
	old_keybuffer = None
	old_wid = None
	result = None
	throbber = ' '

	def draw(self):
		if self.env.cf != self.old_cf or\
				str(self.env.keybuffer) != str(self.old_keybuffer) or\
				self.wid != self.old_wid:
			self.old_wid = self.wid
			self.old_cf = self.env.cf
			self._calc_bar()
		self._print_result(self.result)
		if self.wid > 2:
			self.color('in_titlebar', 'throbber')
			self.win.addnstr(self.y, self.wid - 2, self.throbber, 1)

	def _calc_bar(self):
		bar = Bar()
		self._get_left_part(bar)
		self._get_right_part(bar)
		try:
			bar.shrink_by_cutting(self.wid)
		except ValueError:
			bar.shrink_by_removing(self.wid)
		self.result = bar.combine()
	
	def _get_left_part(self, bar):
		import socket, os
		
		bar.add(os.getenv('LOGNAME'), 'hostname', fixedsize=True)
		bar.add('@', 'hostname', fixedsize=True)
		bar.add(socket.gethostname(), 'hostname', fixedsize=True)

		for path in self.env.pathway:
			if path.islink:
				clr = 'link'
			else:
				clr = 'directory'

			bar.add(path.basename, clr)
			bar.add('/', clr, fixedsize=True)

		if self.env.cf is not None:
			bar.add(self.env.cf.basename, 'file', fixedsize=True)

	def _get_right_part(self, bar):
		kb = str(self.env.keybuffer)
		self.old_keybuffer = kb
		bar.addright(kb, 'keybuffer', fixedsize=True)
		bar.addright('  ', 'space', fixedsize=True)

	def _print_result(self, result):
		import _curses
		self.win.move(self.y, self.x)
		for part in result:
			self.color(*part.lst)
			try:
				self.win.addstr(part.string)
			except _curses.error:
				pass
		self.color_reset()


class Bar(object):
	left = None
	right = None
	gap = None

	def __init__(self):
		self.left = BarSide()
		self.right = BarSide()
		self.gap = BarSide()

	def add(self, *a, **kw):
		self.left.add(*a, **kw)
	
	def addright(self, *a, **kw):
		self.right.add(*a, **kw)

	def sumsize(self):
		return self.left.sumsize() + self.right.sumsize()

	def fixedsize(self):
		return self.left.fixedsize() + self.right.fixedsize()

	def shrink_by_removing(self, wid):
		leftsize = self.left.sumsize()
		rightsize = self.right.sumsize()
		sumsize = leftsize + rightsize

		# remove elemets from the left until it fits
		if sumsize > wid:
			while len(self.left) > 0:
				leftsize -= len(self.left.pop(-1).string)
				if leftsize + rightsize <= wid:
					break
			sumsize = leftsize + rightsize

			# remove elemets from the right until it fits
			if sumsize > wid:
				while len(self.right) > 0:
					rightsize -= len(self.right.pop(0).string)
					if leftsize + rightsize <= wid:
						break
				sumsize = leftsize + rightsize

		if sumsize < wid:
			self.fill_gap(' ', (wid - sumsize), gapwidth=True)
	
	def shrink_by_cutting(self, wid):
		fixedsize = self.fixedsize()
		if wid < fixedsize:
			raise ValueError("Cannot shrink down to that size by cutting")

		leftsize = self.left.sumsize()
		rightsize = self.right.sumsize()
		nonfixed_items = self.left.nonfixed_items()

#		log(leftsize, fixedsize, nonfixed_items)
		itemsize = int(float(wid - rightsize - fixedsize) / nonfixed_items) + 1
#		log(itemsize)

		for item in self.left:
			if not item.fixed:
				item.cut_off_to(itemsize)

		self.fill_gap(' ', wid, gapwidth=False)

	def fill_gap(self, char, wid, gapwidth=False):
		del self.gap[:]

		if not gapwidth:
			wid = wid - self.sumsize()

		if wid > 0:
			self.gap.add(char * wid, 'space')
	
	def combine(self):
		return self.left + self.gap + self.right


class BarSide(list):
	def add(self, string, *lst, **kw):
		cs = ColoredString(string, 'in_titlebar', *lst)
		if 'fixedsize' in kw:
			cs.fixed = kw['fixedsize']
		self.append(cs)
	
	def sumsize(self):
		return sum(len(item) for item in self)

	def fixedsize(self):
		n = 0
		for item in self:
			if item.fixed:
				n += len(item)
			else:
				n += 1
		return n
	
	def nonfixed_items(self):
		return sum(1 for item in self if not item.fixed)


class ColoredString(object):
	fixed = False

	def __init__(self, string, *lst):
		self.string = string
		self.lst = lst
	
	def cut_off(self, n):
		n = max(n, min(len(self.string), 1))
		self.string = self.string[:-n]

	def cut_off_to(self, n):
		self.string = self.string[:n]
	
	def __len__(self):
		return len(self.string)

	def __str__(self):
		return self.string
