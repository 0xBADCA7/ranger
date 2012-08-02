# Copyright (C) 2009, 2010, 2011  Roman Zimbelmann <romanz@lavabit.com>
# This software is distributed under the terms of the GNU GPL version 3.

"""Shared objects contain singleton variables which can be
inherited, essentially acting like global variables."""

from ranger.ext.lazy_property import lazy_property
import os.path

class Awareness(object):
	pass

class EnvironmentAware(Awareness):
	# This creates an instance implicitly, mainly for unit tests
	@lazy_property
	def env(self):
		from ranger.core.environment import Environment
		return Environment(".")

class FileManagerAware(Awareness):
	# This creates an instance implicitly, mainly for unit tests
	@lazy_property
	def fm(self):
		from ranger.core.fm import FM
		return FM()

class SettingsAware(Awareness):
	# This creates an instance implicitly, mainly for unit tests
	@lazy_property
	def settings(self):
		from ranger.ext.openstruct import OpenStruct
		return OpenStruct()

	@staticmethod
	def _setup(clean=True):
		from ranger.container.settingobject import SettingObject, \
				ALLOWED_SETTINGS
		import ranger
		import sys
		settings = SettingObject()

		from ranger.gui.colorscheme import _colorscheme_name_to_class
		settings.signal_bind('setopt.colorscheme',
				_colorscheme_name_to_class, priority=1)

		def after_setting_preview_script(signal):
			if isinstance(signal.value, str):
				signal.value = os.path.expanduser(signal.value)
				if not os.path.exists(signal.value):
					signal.value = None
		settings.signal_bind('setopt.preview_script',
				after_setting_preview_script, priority=1)
		def after_setting_use_preview_script(signal):
			if signal.fm.settings.preview_script is None and signal.value \
					and not signal.previous:
				signal.fm.notify("Preview script undefined or not found!",
						bad=True)
		settings.signal_bind('setopt.use_preview_script',
				after_setting_use_preview_script, priority=1)

		if not clean:
			# add the custom options to the list of setting sources
			sys.path[0:0] = [ranger.arg.confdir]
			try:
				import options as my_options
			except ImportError:
				# XXX: This mistakenly ignores ImportErrors inside options.py
				# It should only ignore missing options.py instead.
				pass
			else:
				settings._setting_sources.append(my_options)
			del sys.path[0]

		from ranger.config import options as default_options
		settings._setting_sources.append(default_options)
		assert all(hasattr(default_options, setting) \
				for setting in ALLOWED_SETTINGS), \
				"Ensure that all options are defined in the defaults!"
		SettingsAware.settings = settings
