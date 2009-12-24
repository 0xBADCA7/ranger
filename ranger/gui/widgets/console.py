"""The Console widget implements a vim-like console for entering
commands, searching and executing files."""
from . import Widget
from ranger import commands
import curses
from collections import deque

DEFAULT_HISTORY = 0
SEARCH_HISTORY = 1
QUICKOPEN_HISTORY = 2

class Console(Widget):
	mode = None
	visible = False
	commandlist = None
	last_cursor_mode = 1
	prompt = ':'
	copy = ''
	tab_deque = None
	original_line = None
	history = None
	histories = None
	override = None

	def __init__(self, win):
		from ranger.container import CommandList, History
		Widget.__init__(self, win)
		self.commandlist = CommandList()
		self.settings.keys.initialize_console_commands(self.commandlist)
		self.clear()
		self.histories = [None] * 3
		self.histories[DEFAULT_HISTORY] = History()
		self.histories[SEARCH_HISTORY] = History()
		self.histories[QUICKOPEN_HISTORY] = History()
	
	def init(self):
		"""override this. Called directly after class change"""

	def draw(self):
		if self.mode is None:
			return
		self.win.addstr(self.y, self.x, self.prompt + self.line)

	def finalize(self):
		try:
			self.win.move(self.y, self.x + self.pos + len(self.prompt))
		except:
			pass

	def open(self, mode, string=''):
		if mode not in self.mode_classes:
			return False

		self.last_cursor_mode = curses.curs_set(1)
		self.mode = mode
		self.__class__ = self.mode_classes[mode]
		self.history = self.histories[DEFAULT_HISTORY]
		self.init()
		self.tab_deque = None
		self.focused = True
		self.visible = True
		self.line = string
		self.pos = len(string)
		self.history.add('')
		return True

	def close(self):
		curses.curs_set(self.last_cursor_mode)
		self.add_to_history()
		self.clear()
		self.__class__ = Console
		self.focused = False
		self.visible = False
		if hasattr(self, 'on_close'):
			self.on_close()
	
	def clear(self):
		self.pos = 0
		self.line = ''
	
	def press(self, key):
		from curses.ascii import ctrl, ESC

		try:
			cmd = self.commandlist[self.env.keybuffer.tuple_with_numbers()]
		except KeyError:
			self.env.key_clear()
			return

		if cmd == self.commandlist.dummy_object:
			return

		cmd.execute(self)
		self.env.key_clear()

	def type_key(self, key):
		self.tab_deque = None

		if isinstance(key, int):
			key = chr(key)

		if self.pos == len(self.line):
			self.line += key
		else:
			self.line = self.line[:self.pos] + key + self.line[self.pos:]

		self.pos += len(key)
		self.on_line_change()

	def history_move(self, n):
		from ranger.container.history import HistoryEmptyException
		try:
			current = self.history.current()
		except HistoryEmptyException:
			pass
		else:
			if self.line != current and self.line != self.history.top():
				self.history.modify(self.line)
			self.history.move(n)
			current = self.history.current()
			if self.line != current:
				self.line = self.history.current()
				self.pos = len(self.line)
	
	def add_to_history(self):
		self.history.fast_forward()
		self.history.modify(self.line)

	def move(self, relative = 0, absolute = None):
		if absolute is not None:
			if absolute < 0:
				self.pos = len(self.line) + 1 + absolute
			else:
				self.pos = absolute

		self.pos = min(max(0, self.pos + relative), len(self.line))

	def delete_rest(self, direction):
		self.tab_deque = None
		if direction > 0:
			self.copy = self.line[self.pos:]
			self.line = self.line[:self.pos]
		else:
			self.copy = self.line[:self.pos]
			self.line = self.line[self.pos:]
			self.pos = 0
		self.on_line_change()

	def paste(self):
		if self.pos == len(self.line):
			self.line += self.copy
		else:
			self.line = self.line[:self.pos] + self.copy + self.line[self.pos:]
		self.pos += len(self.copy)
		self.on_line_change()

	def delete_word(self):
		self.tab_deque = None
		try:
			i = self.line.rindex(' ', 0, self.pos - 1) + 1
			self.line = self.line[:i] + self.line[self.pos:]
			self.pos = len(self.line)
		except ValueError:
			self.line = ''
			self.pos = 0
		self.on_line_change()
	
	def delete(self, mod):
		self.tab_deque = None
		if mod == -1 and len(self.line) == 0:
			self.close()
		pos = self.pos + mod

		self.line = self.line[0:pos] + self.line[pos+1:]
		self.move(relative = mod)
		self.on_line_change()

	def execute(self):
		self.tab_deque = None
		self.close()

	def tab(self):
		pass

	def on_line_change(self):
		pass


class CommandConsole(Console):
	prompt = ':'

	def execute(self):
		cmd = self._get_cmd()
		if cmd: cmd.execute()

		Console.execute(self)
	
	def tab(self, n=1):
		if self.tab_deque is None:
			tab_result = self._get_tab()

			if isinstance(tab_result, str):
				self.line = tab_result
				self.pos = len(tab_result)
				self.on_line_change()

			elif tab_result == None:
				pass

			elif hasattr(tab_result, '__iter__'):
				self.tab_deque = deque(tab_result)
				self.tab_deque.appendleft(self.line)

		if self.tab_deque is not None:
			self.tab_deque.rotate(-n)
			self.line = self.tab_deque[0]
			self.pos = len(self.line)
			self.on_line_change()

	def _get_cmd(self):
		try:
			command_name = self.line.split()[0]
		except:
			return None

		try:
			command_class = commands.by_name[command_name]
		except KeyError:
			return None

		return command_class(self.line, self.mode)
	
	def _get_tab(self):
		cmd = self._get_cmd()
		if cmd:
			return cmd.tab()
		else:
			return None


class QuickCommandConsole(CommandConsole):
	prompt = '>'
	def on_line_change(self):
		cmd = self._get_cmd()
		if cmd and cmd.quick_open():
			self.execute()


class SearchConsole(Console):
	prompt = '/'

	def init(self):
		self.history = self.histories[SEARCH_HISTORY]

	def execute(self):
		import re
		if self.fm.env.pwd:
			regexp = re.compile(self.line, re.L | re.U | re.I)
			self.fm.env.last_search = regexp
			if self.fm.env.pwd.search(regexp):
				self.fm.env.cf = self.fm.env.pwd.pointed_file
		Console.execute(self)


class OpenConsole(Console):
	prompt = '!'


class QuickOpenConsole(Console):

	"""The QuickOpenConsole allows you to open files with
	pre-defined programs and modes very quickly. By adding flags
	to the command, you can specify precisely how the program is run,
	ie. the d-flag will run it detached from the filemanager.
	"""

	prompt = 'open with: '

	def init(self):
		self.history = self.histories[QUICKOPEN_HISTORY]

	def execute(self):
		split = self.line.split()
		app, flags, mode = self._get_app_flags_mode()
		self.fm.execute_file(
				files = [self.env.cf],
				app = app,
				flags = flags,
				mode = mode )
		Console.execute(self)

	def _get_app_flags_mode(self):
		"""extracts the application, flags and mode from
		a string entered into the "openwith_quick" console.
		"""
		# examples:
		# "mplayer d 1" => ("mplayer", "d", 1)
		# "aunpack 4" => ("aunpack", "", 4)
		# "p" => ("", "p", 0)
		# "" => None

		app = ''
		flags = ''
		mode = 0
		split = self.line.split()

		if len(split) == 0:
			pass

		elif len(split) == 1:
			part = split[0]
			if self._is_app(part):
				app = part
			elif self._is_flags(part):
				flags = part
			elif self._is_mode(part):
				mode = part

		elif len(split) == 2:
			part0 = split[0]
			part1 = split[1]

			if self._is_app(part0):
				app = part0
				if self._is_flags(part1):
					flags = part1
				elif self._is_mode(part1):
					mode = part1
			elif self._is_flags(part0):
				flags = part0
				if self._is_mode(part1):
					mode = part1
			elif self._is_mode(part0):
				mode = part0
				if self._is_flags(part1):
					flags = part1

		elif len(split) >= 3:
			part0 = split[0]
			part1 = split[1]
			part2 = split[2]

			if self._is_app(part0):
				app = part0
				if self._is_flags(part1):
					flags = part1
					if self._is_mode(part2):
						mode = part2
				elif self._is_mode(part1):
					mode = part1
					if self._is_flags(part2):
						flags = part2
			elif self._is_flags(part0):
				flags = part0
				if self._is_mode(part1):
					mode = part1
			elif self._is_mode(part0):
				mode = part0
				if self._is_flags(part1):
					flags = part1

		return app, flags, int(mode)

	def _is_app(self, arg):
		return self.fm.apps.has(arg)

	def _is_flags(self, arg):
		from ranger.applications import ALLOWED_FLAGS
		return all(x in ALLOWED_FLAGS for x in arg)

	def _is_mode(self, arg):
		return all(x in '0123456789' for x in arg)


Console.mode_classes = {
		':': CommandConsole,
		'>': QuickCommandConsole,
		'!': OpenConsole,
		'@': QuickOpenConsole,
		'/': SearchConsole,
		'?': SearchConsole,
}
