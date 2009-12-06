from ranger.gui.widget import Widget as SuperClass
import curses

CONSOLE_MODES = tuple(':@/?>!')
CONSOLE_MODES_DICTIONARY = { '@': 'open with: ' }

class WConsole(SuperClass):
	def __init__(self, win, colorscheme):
		from ranger.command import CommandList
		from ranger.conf import keys
		SuperClass.__init__(self, win, colorscheme)
		self.mode = None
		self.visible = False
		self.commandlist = CommandList()
		keys.initialize_console_commands(self.commandlist)
		self.last_cursor_mode = 1
		self.clear()
		self.prompt = None
		self.execute_funcs = {
				':': WConsole.execute_command,
				'@': WConsole.execute_openwith_quick,
				'/': WConsole.execute_search,
				'?': WConsole.execute_search,
				'>': WConsole.execute_noreturn,
				'!': WConsole.execute_openwith }
	
	def feed_env(self, env):
		self.cf = env.cf

	def draw(self):
		if self.mode is None:
			return
		self.win.addstr(self.y, self.x, self.prompt + self.line)

	def finalize(self):
		try:
			self.win.move(self.y, self.x + self.pos + len(self.prompt))
		except:
			pass

	def open(self, mode):
		if mode not in CONSOLE_MODES:
			return False

		self.last_cursor_mode = curses.curs_set(1)
		self.mode = mode
		try:
			self.prompt = CONSOLE_MODES_DICTIONARY[self.mode]
		except KeyError:
			self.prompt = self.mode
		self.focused = True
		self.visible = True
		return True

	def close(self):
		curses.curs_set(self.last_cursor_mode)
		self.focused = False
		self.visible = False
		if hasattr(self, 'on_close'):
			self.on_close()
	
	def clear(self):
		self.pos = 0
		self.line = ''
	
	def press(self, key, fm, env):
		from curses.ascii import ctrl, ESC
#		from ranger.helper import log
#		log(key)

		try:
			cmd = self.commandlist.paths[env.keybuffer]
		except KeyError:
			env.key_clear()
			return

		if cmd == self.commandlist.dummy_object:
			return

		cmd.execute(self, fm)
		env.key_clear()

	def type_key(self, key):
		if isinstance(key, int):
			key = chr(key)

		if self.pos == len(self.line):
			self.line += key
		else:
			self.line = self.line[:self.pos] + key + self.line[self.pos:]

		self.pos += len(key)

	def move(self, relative = 0, absolute = None):
		if absolute is not None:
			if absolute < 0:
				self.pos = len(self.line) + 1 + absolute
			else:
				self.pos = absolute

		self.pos = min(max(0, self.pos + relative), len(self.line))

	def delete_rest(self, direction):
		if direction > 0:
			self.line = self.line[:self.pos]
		else:
			self.line = self.line[self.pos:]
			self.pos = 0
	
	def delete(self, mod):
		if mod == -1 and len(self.line) == 0:
			self.close()
		pos = self.pos + mod

		self.line = self.line[0:pos] + self.line[pos+1:]
		self.move(relative = mod)

	def execute(self, fm):
		try:
			self.execute_funcs[self.mode] (self, fm)
		except KeyError:
			pass
		self.line = ''
		self.pos = 0
		self.close()

	def execute_search(self, fm):
		import re
		if fm.env.pwd:
#			try:
				regexp = re.compile(self.line, re.L | re.U | re.I)
				fm.env.last_search = regexp
				if fm.env.pwd.search(regexp):
					fm.env.cf = fm.env.pwd.pointed_file
#			except:
#				pass

	def execute_openwith(self, fm):
		line = self.line
		if line[0] == '!':
			fm.execute_file(tuple(line[1:].split()) + (fm.env.cf.path, ))
		else:
			fm.execute_file(tuple(line.split()) + (fm.env.cf.path, ), background = True)

	def execute_openwith_quick(self, fm):
		split = self.line.split()
		app, flags, mode = get_app_flags_mode(self.line, fm)
		fm.execute_file(
				files = [self.cf],
				app = app,
				flags = flags,
				mode = mode )

	def execute_noreturn(self, fm):
		pass

	def execute_command(self, fm):
		pass

def get_app_flags_mode(line, fm):
	app = ''
	flags = ''
	mode = 0
	split = line.split()

	if len(split) == 0:
		pass

	elif len(split) == 1:
		part = split[0]
		if is_app(part, fm):
			app = part
		elif is_flags(part):
			flags = part
		elif is_mode(part):
			mode = part

	elif len(split) == 2:
		part0 = split[0]
		part1 = split[1]

		if is_app(part0, fm):
			app = part0
			if is_flags(part1):
				flags = part1
			elif is_mode(part1):
				mode = part1
		elif is_flags(part0):
			flags = part0
			if is_mode(part1):
				mode = part1
		elif is_mode(part0):
			mode = part0
			if is_flags(part1):
				flags = part1

	elif len(split) >= 3:
		part0 = split[0]
		part1 = split[1]
		part2 = split[2]

		if is_app(part0, fm):
			app = part0
			if is_flags(part1):
				flags = part1
				if is_mode(part2):
					mode = part2
			elif is_mode(part1):
				mode = part1
				if is_flags(part2):
					flags = part2
		elif is_flags(part0):
			flags = part0
			if is_mode(part1):
				mode = part1
		elif is_mode(part0):
			mode = part0
			if is_flags(part1):
				flags = part1

	return app, flags, int(mode)

def is_app(arg, fm):
	return fm.apps.has(arg)

def is_flags(arg):
	from ranger.applications import ALLOWED_FLAGS
	return all(x in ALLOWED_FLAGS for x in arg)

def is_mode(arg):
	return all(x in '0123456789' for x in arg)


