"""
This is the default ranger configuration file for filetype detection
and application handling.

You can place this file in your ~/.ranger/ directory and it will be used
instead of this one.  Though, to minimize your effort when upgrading ranger,
you may want to subclass CustomApplications rather than making a full copy.
            
This example modifies the behaviour of "feh" and adds a custom media player:

#### start of the ~/.ranger/apps.py example
from ranger.defaults.apps import CustomApplications as DefaultApps
from ranger.api.apps import *
        
class CustomApplications(DefaultApps):
    def app_kaffeine(self, c):
        return tup('kaffeine', *c)

    def app_feh_fullscreen_by_default(self, c):
        return tup('feh', '-F', *c)

    def app_default(self, c):
        if c.file.video or c.file.audio:
            return self.app_kaffeine(c)

        if c.file.image and c.mode == 0:
            return self.app_feh_fullscreen_by_default(c)

        return DefaultApps.app_default(self, c)
#### end of the example
"""

from ranger.api.apps import *

INTERPRETED_LANGUAGES = re.compile(r'''
	^(text|application)\/x-(
		haskell|perl|python|ruby|sh
	)$''', re.VERBOSE)

class CustomApplications(Applications):
	def app_default(self, c):
		"""How to determine the default application?"""
		f = c.file

		if f.extension is not None:
			if f.extension in ('pdf'):
				return self.either(c, 'evince', 'apvlv')
			if f.extension in ('html', 'htm', 'xhtml', 'swf'):
				return self.either(c, 'firefox', 'opera', 'elinks')
			if f.extension in ('swc', 'smc'):
				return self.app_zsnes(c)

		if f.mimetype is not None:
			if INTERPRETED_LANGUAGES.match(f.mimetype):
				return self.app_edit_or_run(c)

		if f.container:
			return self.app_aunpack(c)

		if f.video or f.audio:
			if f.video:
				c.flags += 'd'
			return self.either(c, 'mplayer', 'totem')

		if f.image:
			return self.app_feh(c)

		if f.document:
			return self.app_editor(c)

	# ----------------------------------------- application definitions
	def app_pager(self, c):
		return tup('less', *c)

	@depends_on('vim')
	def app_vim(self, c):
		return tup('vim', *c)

	def app_editor(self, c):
		try:
			default_editor = os.environ['EDITOR']
		except KeyError:
			pass
		else:
			parts = default_editor.split()
			exe_name = os.path.basename(parts[0])
			if exe_name in self.fm.executables:
				return tuple(parts) + tuple(c)

		return self.either(c, 'vim', 'emacs', 'nano')

	@depends_on(app_editor, Applications.app_self)
	def app_edit_or_run(self, c):
		if c.mode is 1:
			return self.app_self(c)
		return self.app_editor(c)

	@depends_on('mplayer')
	def app_mplayer(self, c):
		if c.mode is 1:
			return tup('mplayer', *c)

		elif c.mode is 2:
			args = "mplayer -fs -sid 0 -vfm ffmpeg -lavdopts " \
					"lowres=1:fast:skiploopfilter=all:threads=8".split()
			args.extend(c)
			return tup(*args)

		elif c.mode is 3:
			return tup('mplayer', '-mixer', 'software', *c)

		else:
			return tup('mplayer', '-fs', *c)

	@depends_on('mirage')
	def app_mirage(self, c):
		c.flags += 'd'

		return tup('mirage', *c)

	@depends_on('feh')
	def app_feh(self, c):
		arg = {1: '--bg-scale', 2: '--bg-tile', 3: '--bg-center'}

		c.flags += 'd'

		if c.mode in arg:
			return tup('feh', arg[c.mode], c.file.path)
		if c.mode is 4:
			return tup('gimp', *c)
		return tup('feh', *c)

	@depends_on('aunpack')
	def app_aunpack(self, c):
		if c.mode is 0:
			c.flags += 'p'
			return tup('aunpack', '-l', c.file.path)
		return tup('aunpack', c.file.path)

	@depends_on('apvlv')
	def app_apvlv(self, c):
		c.flags += 'd'
		return tup('apvlv', *c)

	@depends_on('make')
	def app_make(self, c):
		if c.mode is 0:
			return tup("make")
		if c.mode is 1:
			return tup("make", "install")
		if c.mode is 2:
			return tup("make", "clear")

	@depends_on('elinks')
	def app_elinks(self, c):
		c.flags += 'D'
		return tup('elinks', *c)

	@depends_on('opera')
	def app_opera(self, c):
		return tup('opera', *c)

	@depends_on('firefox')
	def app_firefox(self, c):
		return tup("firefox", *c)

	@depends_on('javac')
	def app_javac(self, c):
		return tup("javac", *c)

	@depends_on('java')
	def app_java(self, c):
		def strip_extensions(file):
			if '.' in file.basename:
				return file.path[:file.path.index('.')]
			return file.path
		files_without_extensions = map(strip_extensions, c.files)
		return tup("java", files_without_extensions)

	@depends_on('zsnes')
	def app_zsnes(self, c):
		return tup("zsnes", c.file.path)

	@depends_on('evince')
	def app_evince(self, c):
		return tup("evince", *c)

	@depends_on('wine')
	def app_wine(self, c):
		return tup("wine", c.file.path)

	@depends_on('totem')
	def app_totem(self, c):
		if c.mode is 0:
			return tup("totem", "--fullscreen", *c)
		if c.mode is 1:
			return tup("totem", *c)
