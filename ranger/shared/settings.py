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

from ranger.ext.openstruct import OpenStruct

ALLOWED_SETTINGS = {
	'show_hidden': bool,
	'show_cursor': bool,
	'autosave_bookmarks': bool,
	'collapse_preview': bool,
	'sort': str,
	'reverse': bool,
	'directories_first': bool,
	'update_title': bool,
	'max_filesize_for_preview': (int, type(None)),
	'max_history_size': (int, type(None)),
	'scroll_offset': int,
	'preview_files': bool,
	'flushinput': bool,
	'colorscheme': object,
	'hidden_filter': lambda x: isinstance(x, str) or hasattr(x, 'match'),
}

# -- globalize the settings --
class SettingsAware(object):
	settings = OpenStruct()

	@staticmethod
	def _setup():
		from inspect import isclass, ismodule
		from ranger.gui.colorscheme import ColorScheme

		# overwrite single default options with custom options
		from ranger.defaults import options
		try:
			import options as custom_options
			for setting in ALLOWED_SETTINGS:
				if hasattr(custom_options, setting):
					setattr(options, setting, getattr(custom_options, setting))
				elif not hasattr(options, setting):
					raise Exception("This option was not defined: " + setting)
		except ImportError:
			pass

		assert check_option_types(options)

		try:
			import apps
		except ImportError:
			from ranger.defaults import apps

		try:
			import keys
		except ImportError:
			from ranger.defaults import keys


		# If a module is specified as the colorscheme, replace it with one
		# valid colorscheme inside that module.

		if isclass(options.colorscheme) and \
				issubclass(options.colorscheme, ColorScheme):
			options.colorscheme = options.colorscheme()

		elif ismodule(options.colorscheme):
			for var_name in dir(options.colorscheme):
				var = getattr(options.colorscheme, var_name)
				if var != ColorScheme and isclass(var) \
						and issubclass(var, ColorScheme):
					options.colorscheme = var()
					break
			else:
				raise Exception("The module contains no valid colorscheme!")

		else:
			raise Exception("Cannot locate colorscheme!")

		for setting in ALLOWED_SETTINGS:
			SettingsAware.settings[setting] = getattr(options, setting)

		SettingsAware.settings.keys = keys
		SettingsAware.settings.apps = apps


def check_option_types(opt):
	import inspect
	for name, typ in ALLOWED_SETTINGS.items():
		optvalue = getattr(opt, name)
		if inspect.isfunction(typ):
			assert typ(optvalue), \
				"The option `" + name + "' has an incorrect type!"
		else:
			assert isinstance(optvalue, typ), \
				"The option `" + name + "' has an incorrect type!"\
				" Expected " + str(typ) + "!"
	return True
