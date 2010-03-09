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

from string import ascii_lowercase
from inspect import isfunction, getargspec
from ranger.ext.tree import Tree

MAX_ALIAS_RECURSION = 20
DIRKEY = 9001
ANYKEY = 9002
FUNC = 'func'
DIRECTION = 'direction'
DIRARG = 'dir'
ALIASARG = 'alias'

class Direction(object):
	"""An object with a down and right method"""
	def __init__(self, down=0, right=0):
		self.down = down
		self.right = right

	def copy(self):
		new = type(self)()
		new.__dict__.update(self.__dict__)
		return new

	def __mul__(self, other):
		copy = self.copy()
		if other is not None:
			copy.down *= other
			copy.right *= other
		return copy
	__rmul__ = __mul__

def to_string(i):
	"""convert a ord'd integer to a string"""
	try:
		return chr(i)
	except ValueError:
		return '?'

def is_ascii_digit(n):
	return n >= 48 and n <= 57

class CommandArgs(object):
	"""The arguments which are passed to a keybinding function"""
	def __init__(self, fm, widget, keybuffer):
		self.fm = fm
		self.wdg = widget
		self.keybuffer = keybuffer
		self.n = keybuffer.quant
		self.direction = keybuffer.directions and keybuffer.directions[0] or None
		self.directions = keybuffer.directions
		self.keys = str(keybuffer)
		self.matches = keybuffer.matches
		self.binding = keybuffer.command

	@staticmethod
	def from_widget(self, widget):
		return CommandArgs(displayable.fm, \
				displayable, displayable.env.keybuffer)

class KeyMap(Tree):
	"""Contains a tree with all the keybindings"""
	def add(self, *args, **keywords):
		if keywords:
			return self.add_binding(*args, **keywords)
		firstarg = args[0]
		if isfunction(firstarg):
			keywords[FUNC] = firstarg
			return self.add_binding(*args[1:], **keywords)
		def decorator_function(func):
			keywords = {FUNC:func}
			self.add(*args, **keywords)
			return func
		return decorator_function

	def add_binding(self, *keys, **actions):
		assert keys
		bind = Binding(keys, actions)
		for key in keys:
			self.set(translate_keys(key), bind)

	def __getitem__(self, key):
		return self.traverse(translate_keys(key))

class Binding(object):
	"""The keybinding object"""
	def __init__(self, keys, actions):
		assert hasattr(keys, '__iter__')
		assert isinstance(actions, dict)
		self.actions = actions
		try:
			self.function = self.actions[FUNC]
		except KeyError:
			self.function = None
			self.has_direction = False
		else:
			argnames = getargspec(self.function)[0]
			try:
				self.has_direction = actions['with_direction']
			except KeyError:
				self.has_direction = DIRECTION in argnames
		try:
			self.direction = self.actions[DIRARG]
		except KeyError:
			self.direction = None
		try:
			alias = self.actions[ALIASARG]
		except KeyError:
			self.alias = None
		else:
			self.alias = translate_keys(alias)

class KeyBuffer(object):
	"""The evaluator and storage for pressed keys"""
	def __init__(self, keymap, direction_keys):
		self.keymap = keymap
		self.direction_keys = direction_keys
		self.clear()

	def add(self, key):
		if self.failure:
			return None
		assert isinstance(key, int)
		assert key >= 0

		# evaluate quantifiers
		if self.eval_quantifier and self._do_eval_quantifier(key):
			return

		# evaluate the command
		if self.eval_command and self._do_eval_command(key):
			return

		# evaluate (the first number of) the direction-quantifier
		if self.eval_quantifier and self._do_eval_quantifier(key):
			return

		# evaluate direction keys {j,k,gg,pagedown,...}
		if not self.eval_command:
			self._do_eval_direction(key)

	def _do_eval_direction(self, key):
		# swap quant and direction_quant in bindings like '<dir>'
		if self.quant is not None and self.command is None \
		and self.direction_quant is None:
			self.direction_quant = self.quant
			self.quant = None

		try:
			assert isinstance(self.dir_tree_pointer, dict)
			self.dir_tree_pointer = self.dir_tree_pointer[key]
		except KeyError:
			self.failure = True
		else:
			self._direction_try_to_finish()

	def _direction_try_to_finish(self, rec=MAX_ALIAS_RECURSION):
		if rec <= 0:
			self.failure = True
			return None
		if not isinstance(self.dir_tree_pointer, dict):
			match = self.dir_tree_pointer
			assert isinstance(match, Binding)
			if 'alias' in match.actions:
				self.dir_tree_pointer = self.direction_keys.traverse(
					match.alias)
				self._direction_try_to_finish(rec - 1)
			else:
				direction = match.actions['dir'] * self.direction_quant
				self.directions.append(direction)
				self.direction_quant = None
				self.eval_command = True
				self._try_to_finish()

	def _do_eval_quantifier(self, key):
		if self.eval_command:
			tree = self.tree_pointer
		else:
			tree = self.dir_tree_pointer
		if is_ascii_digit(key) and ANYKEY not in tree:
			attr = self.eval_command and 'quant' or 'direction_quant'
			if getattr(self, attr) is None:
				setattr(self, attr, 0)
			setattr(self, attr, getattr(self, attr) * 10 + key - 48)
		else:
			self.eval_quantifier = False
			return None
		return True

	def _do_eval_command(self, key):
		try:
			assert isinstance(self.tree_pointer, dict)
			self.tree_pointer = self.tree_pointer[key]
		except TypeError:
			print(self.tree_pointer)
			self.failure = True
			return None
		except KeyError:
			if DIRKEY in self.tree_pointer:
				self.eval_command = False
				self.eval_quantifier = True
				self.tree_pointer = self.tree_pointer[DIRKEY]
				assert isinstance(self.tree_pointer, (Binding, dict))
				self.dir_tree_pointer = self.direction_keys._tree
			elif ANYKEY in self.tree_pointer:
				self.matches.append(key)
				self.tree_pointer = self.tree_pointer[ANYKEY]
				assert isinstance(self.tree_pointer, (Binding, dict))
				self._try_to_finish()
			else:
				self.failure = True
				return None
		else:
			self._try_to_finish()

	def _try_to_finish(self, rec=MAX_ALIAS_RECURSION):
		if rec <= 0:
			self.failure = True
			return None
		assert isinstance(self.tree_pointer, (Binding, dict, KeyMap))
		if isinstance(self.tree_pointer, KeyMap):
			self.tree_pointer = self.tree_pointer._tree
		if isinstance(self.tree_pointer, Binding):
			if 'alias' in self.tree_pointer.actions:
				self.tree_pointer = self.keymap.traverse(
					translate_keys(self.tree_pointer.actions['alias']))
				self._try_to_finish(rec - 1)
			else:
				self.command = self.tree_pointer
				self.done = True

	def clear(self):
		self.failure = False
		self.done = False
		self.quant = None
		self.matches = []
		self.command = None
		self.direction_quant = None
		self.directions = []
		self.all_keys = []
		self.tree_pointer = self.keymap._tree
		self.dir_tree_pointer = self.direction_keys._tree

		self.eval_quantifier = True
		self.eval_command = True

	def __str__(self):
		"""returns a concatenation of all characters"""
		return "".join(to_string(c) for c in self.all_keys)

	def simulate_press(self, string):
		for char in translate_keys(string):
			self.add(char)
			if self.done:
				return self.command
			if self.failure:
				break

key_map = {
	'dir': DIRKEY,
	'any': ANYKEY,
	'cr': ord("\n"),
	'enter': ord("\n"),
	'space': ord(" "),
	'space': ord(" "),
	'tab': ord('\t'),
}
for char in ascii_lowercase:
	key_map['c-' + char] = ord(char) - 96

def translate_keys(obj):
	"""
	Translate a keybinding to a sequence of integers

	Example:
	lol<CR>   =>   (108, 111, 108, 10)
	"""
	assert isinstance(obj, (tuple, int, str))
	if isinstance(obj, tuple):
		for char in obj:
			yield char
	elif isinstance(obj, int):
		yield obj
	elif isinstance(obj, str):
		in_brackets = False
		bracket_content = None
		for char in obj:
			if in_brackets:
				if char == '>':
					in_brackets = False
					string = ''.join(bracket_content).lower()
					try:
						yield key_map[string]
					except KeyError:
						yield ord('<')
						for c in bracket_content:
							yield ord(c)
						yield ord('>')
				else:
					bracket_content.append(char)
			else:
				if char == '<':
					in_brackets = True
					bracket_content = []
				else:
					yield ord(char)
		if in_brackets:
			yield ord('<')
			for c in bracket_content:
				yield ord(c)
