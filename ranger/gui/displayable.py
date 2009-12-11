from ranger.shared import FileManagerAware, EnvironmentAware, SettingsAware

class Displayable(EnvironmentAware, FileManagerAware, SettingsAware):
	focused = False
	visible = True
	win = None
	colorscheme = None

	def __init__(self, win):
		self.resize(0, 0, 0, 0)
		self.colorscheme = self.env.settings.colorscheme

		if win is not None:
			self.win = win

	def __nonzero__(self):
		"""Always True"""
		return True

	def color(self, keylist = None, *keys):
		"""Change the colors from now on."""
		keys = combine(keylist, keys)
		self.win.attrset(self.colorscheme.get_attr(*keys))

	def color_at(self, y, x, wid, keylist = None, *keys):
		"""Change the colors at the specified position"""
		keys = combine(keylist, keys)
		self.win.chgat(y, x, wid, self.colorscheme.get_attr(*keys))
	
	def color_reset(self):
		"""Change the colors to the default colors"""
		Displayable.color(self, 'reset')

	def draw(self):
		"""Draw the object. Called on every main iteration.
Containers should call draw() on their contained objects here.
Override this!"""

	def destroy(self):
		"""Called when the object is destroyed.
Override this!"""

	def contains_point(self, y, x):
		"""Test if the point lies within the boundaries of this object"""
		return (x >= self.x and x < self.x + self.wid) and \
				(y >= self.y and y < self.y + self.hei)

	def click(self, event):
		"""Called when a mouse key is pressed and self.focused is True.
Override this!"""
		pass

	def press(self, key):
		"""Called when a key is pressed and self.focused is True.
Override this!"""
		pass
	
	def draw(self):
		"""Draw displayable. Called on every main iteration.
Override this!"""
		pass

	def finalize(self):
		"""Called after every displayable is done drawing.
Override this!"""
		pass

	def resize(self, y, x, hei=None, wid=None):
		"""Resize the widget"""
		try:
			maxy, maxx = self.env.termsize
		except TypeError:
			pass
		else:
			wid = wid or maxx - x
			hei = hei or maxy - y

			if x + wid > maxx and y + hei > maxy:
				raise OutOfBoundsException("X and Y out of bounds!")

			if x + wid > maxx:
				raise OutOfBoundsException("X out of bounds!")

			if y + hei > maxy:
				raise OutOfBoundsException("Y out of bounds!")

		self.x = x
		self.y = y
		self.wid = wid
		self.hei = hei


class DisplayableContainer(Displayable):
	container = None
	def __init__(self, win):
		Displayable.__init__(self, win)
		self.container = []

	def draw(self):
		"""Recursively called on objects in container"""
		for displayable in self.container:
			if displayable.visible:
				displayable.draw()

	def finalize(self):
		"""Recursively called on objects in container"""
		for displayable in self.container:
			if displayable.visible:
				displayable.finalize()
	
	def get_focused_obj(self):
		"""Finds a focused displayable object in the container."""
		for displayable in self.container:
			if displayable.focused:
				return displayable
			try:
				obj = displayable.get_focused_obj()
			except AttributeError:
				pass
			else:
				if obj is not None:
					return obj
		return None

	def press(self, key):
		"""Recursively called on objects in container"""
		focused_obj = self.get_focused_obj()

		if focused_obj:
			focused_obj.press(key)
			return True
		return False
	
	def click(self, event):
		"""Recursively called on objects in container"""
		focused_obj = self.get_focused_obj()
		if focused_obj:
			focused_obj.press(key)
			return True
		return False

	def add_obj(self, obj):
		self.container.append(obj)
	
	def destroy(self):
		"""Recursively called on objects in container"""
		for displayable in self.container:
			displayable.destroy()

#	def resize(self):
#		"""Recursively called on objects in container"""
#		for displayable in container:
#			displayable.resize()

class OutOfBoundsException(Exception):
	pass

def combine(seq, tup):
	"""Add seq and tup. Ensures that the result is a tuple."""
	try:
		if isinstance(seq, str): raise TypeError
		return tuple(tuple(seq) + tup)
	except TypeError:
		try:
			return tuple((seq, ) + tup)
		except:
			return ()
