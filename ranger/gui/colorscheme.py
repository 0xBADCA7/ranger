CONTEXT_KEYS = ['reset', 'wdisplay', 'wstatusbar', 'wtitlebar', 'wconsole', 'directory', 'file', 'maindisplay', 'executable', 'media', 'link', 'broken', 'selected', 'empty']

class ColorSchemeContext():
	pass

class ColorScheme():
	def __init__(self):
		self.cache = {}

	def get(self, *keys):
		try:
			return self.cache[keys]

		except KeyError:
			context = ColorSchemeContext()

			for key in CONTEXT_KEYS:
				context.__dict__[key] = (key in keys)

			color = self.use(context)
			self.cache[keys] = color
			return color

	def get_attr(self, *keys):
		from ranger.gui.color import get_color
		import curses

		fg, bg, attr = self.get(*keys)
		return attr | curses.color_pair(get_color(fg, bg))


	def use(self, context):
		return -1, -1, 0

