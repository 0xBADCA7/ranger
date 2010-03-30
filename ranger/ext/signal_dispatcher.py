# Copyright (C) 2009, 2010  Roman Zimbelmann <romanz@lavabit.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import weakref

class Signal(dict):
	stopped = False
	def __init__(self, **keywords):
		dict.__init__(self, keywords)
		self.__dict__ = self

	def stop(self):
		self.stopped = True


class SignalHandler(object):
	active = True
	regexp = None
	def __init__(self, signal_name, function, priority, pass_signal):
		self.priority = max(0, min(1, priority))
		self.signal_name = signal_name
		self.function = function
		self.pass_signal = pass_signal


class SignalDispatcher(object):
	def __init__(self):
		self._signals = dict()

	signal_clear = __init__

	def signal_bind(self, signal_name, function, priority=0.5, weak=False):
		assert isinstance(signal_name, str)
		try:
			handlers = self._signals[signal_name]
		except:
			handlers = self._signals[signal_name] = []
		nargs = function.__code__.co_argcount - hasattr(function, 'im_func')
		if weak:
			function = weakref.proxy(function)
		handler = SignalHandler(signal_name, function, priority, nargs > 0)
		handlers.append(handler)
		handlers.sort(key=lambda handler: -handler.priority)
		return handler

	def signal_unbind(self, signal_handler):
		try:
			handlers = self._signals[signal_handler.signal_name]
		except:
			pass
		else:
			try:
				handlers.remove(signal_handler)
			except:
				pass

	def signal_emit(self, signal_name, **kw):
		assert isinstance(signal_name, str)
		try:
			handlers = self._signals[signal_name]
		except:
			return
		if not handlers:
			return

		signal = Signal(origin=self, name=signal_name, **kw)

		# propagate
		for handler in tuple(handlers):
			if handler.active:
				try:
					if handler.pass_signal:
						handler.function(signal)
					else:
						handler.function()
					if signal.stopped:
						return
				except ReferenceError:
					handlers.remove(handler)

class RegexpSignalDispatcher(SignalDispatcher):
	"""
	A subclass of SignalDispatcher with regexp matching.
	"""

	def __init__(self):
		SignalDispatcher.__init__(self)
		self._signal_regexes = list()
	_signal_clear = __init__

	def signal_bind(self, signal_name, function, priority=0.5):
		try:
			handlers = self._signals[signal_name]
		except:
			handlers = self._signals[signal_name] = []
			for handler in self._signal_regexes:
				if handler.regexp.match(signal_name):
					handlers.append(handler)
		return SignalDispatcher.signal_bind(self, signal_name, \
				function, priority)

	def signal_bind_regexp(self, regexp, function, priority=0.5):
		if isinstance(regexp, str):
			regexp = re.compile(regexp)
		handler = self.signal_bind('dynamic', function, priority)
		handler.regexp = regexp
		self._signal_regexes.append(handler)
		for signal_name, handlers in self._signals.items():
			if regexp.match(signal_name):
				handlers.append(handler)
			handlers.sort(key=lambda handler: -handler.priority)
		return handler

	def signal_unbind(self, handler):
		self._signal_regexes.remove(handler)
		for handlers in self._signals.values():
			try:
				handlers.remove(handler)
			except ValueError:
				pass

	def signal_emit(self, signal_name, **kw):
		assert isinstance(signal_name, str)
		if not signal_name in self._signals:
			handlers = self._signals[signal_name] = []
			for handler in self._signal_regexes:
				if handler.regexp.match(signal_name):
					handlers.append(handler)
		SignalDispatcher.signal_emit(self, signal_name, **kw)
