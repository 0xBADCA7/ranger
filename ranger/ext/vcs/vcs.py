# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

"""VCS module"""

import os
import subprocess
import threading
import time

# Python2 compatibility
try:
    import queue
except ImportError:
    import Queue as queue  # pylint: disable=import-error
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = OSError  # pylint: disable=redefined-builtin


class VcsError(Exception):
    """VCS exception"""
    pass


class Vcs(object):  # pylint: disable=too-many-instance-attributes
    """
    This class represents a version controlled path, abstracting the usual
    operations from the different supported backends.

    The backends are declared in REPOTYPES, and are derived
    classes from Vcs with the following restrictions:

     * Override ALL interface methods
     * Only override interface methods
     * Do NOT modify internal state. All internal state is handled by Vcs

    """

    # These are abstracted revisions, representing the current index (staged files),
    # the current head and nothing. Every backend should redefine them if the
    # version control has a similar concept, or implement _sanitize_rev method to
    # clean the rev before using them
    INDEX = 'INDEX'
    HEAD = 'HEAD'
    NONE = 'NONE'

    # Backends
    REPOTYPES = {
        'bzr': {'class': 'Bzr', 'setting': 'vcs_backend_bzr'},
        'git': {'class': 'Git', 'setting': 'vcs_backend_git'},
        'hg': {'class': 'Hg', 'setting': 'vcs_backend_hg'},
        'svn': {'class': 'SVN', 'setting': 'vcs_backend_svn'},
    }

    # Possible directory statuses in order of importance
    # statuses that should not be inherited from subpaths are disabled
    DIRSTATUSES = (
        'conflict',
        'untracked',
        'deleted',
        'changed',
        'staged',
        # 'ignored',
        'sync',
        # 'none',
        'unknown',
    )

    def __init__(self, dirobj):
        self.obj = dirobj
        self.path = dirobj.path
        self.repotypes_settings = set(
            repotype for repotype, values in self.REPOTYPES.items()
            if getattr(dirobj.settings, values['setting']) in ('enabled', 'local')
        )

        self.root, self.repodir, self.repotype, self.links = self._find_root(self.path)
        self.is_root = True if self.obj.path == self.root else False
        self.in_repodir = False
        self.rootvcs = None
        self.track = False

        if self.root:
            if self.is_root:
                self.rootvcs = self
                self.__class__ = globals()[self.REPOTYPES[self.repotype]['class'] + 'Root']

                if not os.access(self.repodir, os.R_OK):
                    self.obj.vcsremotestatus = 'unknown'
                    self.obj.vcsstatus = 'unknown'
                    return

                self.track = True
            else:
                self.rootvcs = dirobj.fm.get_directory(self.root).vcs
                self.rootvcs.check()
                if self.rootvcs.root is None:
                    return
                self.rootvcs.links |= self.links
                self.__class__ = globals()[self.REPOTYPES[self.repotype]['class']]
                self.track = self.rootvcs.track

                if self.path == self.repodir or self.path.startswith(self.repodir + '/'):
                    self.in_repodir = True
                    self.track = False

    # Generic

    def _run(self, args, path=None, catchout=True, retbytes=False):
        """Run a command"""
        cmd = [self.repotype] + args
        if path is None:
            path = self.path

        with open(os.devnull, 'w') as devnull:
            try:
                if catchout:
                    output = subprocess.check_output(cmd, cwd=path, stderr=devnull)
                    return output if retbytes else output.decode('UTF-8')
                else:
                    subprocess.check_call(cmd, cwd=path, stdout=devnull, stderr=devnull)
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise VcsError('{0:s}: {1:s}'.format(str(cmd), path))

    def _get_repotype(self, path):
        """Get type for path"""
        for repotype in self.repotypes_settings:
            repodir = os.path.join(path, '.' + repotype)
            if os.path.exists(repodir):
                return (repodir, repotype)
        return (None, None)

    def _find_root(self, path):
        """Finds root path"""
        links = set()
        while True:
            if os.path.islink(path):
                links.add(path)
                relpath = os.path.relpath(self.path, path)
                path = os.path.realpath(path)
                self.path = os.path.normpath(os.path.join(path, relpath))

            repodir, repotype = self._get_repotype(path)
            if repodir:
                return (path, repodir, repotype, links)

            path_old = path
            path = os.path.dirname(path)
            if path == path_old:
                break

        return (None, None, None, None)

    def check(self):
        """Check health"""
        if not self.in_repodir \
                and (not self.track or (not self.is_root and self._get_repotype(self.path)[0])):
            self.__init__(self.obj)
            return False
        elif self.track and not os.path.exists(self.repodir):
            self.rootvcs.update_tree(purge=True)  # pylint: disable=no-member
            return False
        return True

    # Action interface

    def action_add(self, filelist):
        """Adds files to the index"""
        raise NotImplementedError

    def action_reset(self, filelist):
        """Removes files from the index"""
        raise NotImplementedError

    # Data interface

    def data_status_root(self):
        """Returns status of self.root cheaply"""
        raise NotImplementedError

    def data_status_subpaths(self):
        """Returns a dict indexed by subpaths not in sync with their status as values.
           Paths are given relative to self.root"""
        raise NotImplementedError

    def data_status_remote(self):
        """
        Returns remote status of repository
        One of ('sync', 'ahead', 'behind', 'diverged', 'none')
        """
        raise NotImplementedError

    def data_branch(self):
        """Returns the current named branch, if this makes sense for the backend. None otherwise"""
        raise NotImplementedError

    def data_info(self, rev=None):
        """Returns info string about revision rev. None in special cases"""
        raise NotImplementedError


class VcsRoot(Vcs):  # pylint: disable=abstract-method
    """Vcs root"""
    rootinit = False
    head = None
    branch = None
    updatetime = None
    status_subpaths = None

    def _status_root(self):
        """Returns root status"""
        if self.status_subpaths is None:
            return 'none'

        statuses = set(status for path, status in self.status_subpaths.items())
        for status in self.DIRSTATUSES:
            if status in statuses:
                return status
        return 'sync'

    def init_root(self):
        """Initialize root cheaply"""
        try:
            self.head = self.data_info(self.HEAD)
            self.branch = self.data_branch()
            self.obj.vcsremotestatus = self.data_status_remote()
            self.obj.vcsstatus = self.data_status_root()
        except VcsError:
            self.update_tree(purge=True)
            return False
        self.rootinit = True
        return True

    def _update_walk(self, path, purge):  # pylint: disable=too-many-branches
        """Update walk"""
        for wroot, wdirs, _ in os.walk(path):
            # Only update loaded directories
            try:
                wrootobj = self.obj.fm.directories[wroot]
            except KeyError:
                wdirs[:] = []
                continue
            if wrootobj.content_loaded:
                has_vcschild = False
                for fileobj in wrootobj.files_all:
                    if purge:
                        if fileobj.is_directory:
                            fileobj.vcsstatus = None
                            fileobj.vcs.__init__(fileobj)
                        else:
                            fileobj.vcsstatus = None
                        continue

                    if fileobj.is_directory:
                        fileobj.vcs.check()
                        if not fileobj.vcs.track:
                            continue
                        if fileobj.vcs.is_root:
                            has_vcschild = True
                        else:
                            fileobj.vcsstatus = self.status_subpath(
                                fileobj.path, is_directory=True)
                    else:
                        fileobj.vcsstatus = self.status_subpath(fileobj.path)
                wrootobj.has_vcschild = has_vcschild

            # Remove dead directories
            for wdir in list(wdirs):
                try:
                    wdir_obj = self.obj.fm.directories[os.path.join(wroot, wdir)]
                except KeyError:
                    wdirs.remove(wdir)
                    continue
                if wdir_obj.vcs.is_root or not wdir_obj.vcs.track:
                    wdirs.remove(wdir)

    def update_tree(self, purge=False):
        """Update tree state"""
        self._update_walk(self.path, purge)
        for path in list(self.links):
            self._update_walk(path, purge)
            try:
                dirobj = self.obj.fm.directories[path]
            except KeyError:
                self.links.remove(path)
                continue
            if purge:
                dirobj.vcsstatus = None
                dirobj.vcs.__init__(dirobj)
            elif dirobj.vcs.path == self.path:
                dirobj.vcsremotestatus = self.obj.vcsremotestatus
                dirobj.vcsstatus = self.obj.vcsstatus
            else:
                dirobj.vcsstatus = self.status_subpath(
                    os.path.realpath(dirobj.path), is_directory=True)
        if purge:
            self.__init__(self.obj)

    def update_root(self):
        """Update root state"""
        try:
            self.head = self.data_info(self.HEAD)
            self.branch = self.data_branch()
            self.status_subpaths = self.data_status_subpaths()
            self.obj.vcsremotestatus = self.data_status_remote()
            self.obj.vcsstatus = self._status_root()
        except VcsError:
            self.update_tree(purge=True)
            return False
        self.rootinit = True
        self.updatetime = time.time()
        return True

    def check_outdated(self):
        """Check if root is outdated"""
        if self.updatetime is None:
            return True

        for wroot, wdirs, _ in os.walk(self.path):
            wrootobj = self.obj.fm.get_directory(wroot)
            wrootobj.load_if_outdated()
            if wroot != self.path and wrootobj.vcs.is_root:
                wdirs[:] = []
                continue

            if wrootobj.stat and self.updatetime < wrootobj.stat.st_mtime:
                return True
            if wrootobj.files_all:
                for wfile in wrootobj.files_all:
                    if wfile.stat and self.updatetime < wfile.stat.st_mtime:
                        return True
        return False

    def status_subpath(self, path, is_directory=False):
        """
        Returns the status of path

        path needs to be self.obj.path or subpath thereof
        """
        if self.status_subpaths is None:
            return 'none'

        relpath = os.path.relpath(path, self.path)

        # check if relpath or its parents has a status
        tmppath = relpath
        while tmppath:
            if tmppath in self.status_subpaths:
                return self.status_subpaths[tmppath]
            tmppath = os.path.dirname(tmppath)

        # check if path contains some file in status
        if is_directory:
            statuses = set(status for subpath, status in self.status_subpaths.items()
                           if subpath.startswith(relpath + '/'))
            for status in self.DIRSTATUSES:
                if status in statuses:
                    return status
        return 'sync'


class VcsThread(threading.Thread):  # pylint: disable=too-many-instance-attributes
    """VCS thread"""
    def __init__(self, ui):
        super(VcsThread, self).__init__()
        self.daemon = True
        self.ui = ui  # pylint: disable=invalid-name
        self.queue = queue.Queue()
        self.awoken = threading.Event()
        self.timestamp = time.time()
        self.redraw = False
        self.roots = set()

    def _hindered(self):
        """Check for hinders"""
        for column in self.ui.browser.columns:
            if column.target and column.target.is_directory and column.target.flat:
                return True
        return False

    def _is_targeted(self, dirobj):
        ''' Check if dirobj is targeted '''
        if not self.ui.browser.main_column:
            return False
        target = self.ui.browser.main_column.target
        if target and target.is_directory and target.path == dirobj.path:
            return True
        return False

    def _update_files(self, fileobjs):
        ''' Update files '''
        if not fileobjs:
            return False

        has_vcschild = False
        for fileobj in fileobjs:
            if not fileobj.is_directory or not fileobj.vcs or not fileobj.vcs.track:
                continue

            if fileobj.vcs.is_root:
                has_vcschild = True
                if not fileobj.vcs.rootinit and not self._is_targeted(fileobj):
                    fileobj.vcs.init_root()
                    self.roots.add(fileobj.vcs.path)
                    self.redraw = True

            elif fileobj.is_link:
                rootvcs = fileobj.vcs.rootvcs
                realpath = os.path.realpath(fileobj.path)
                if realpath == fileobj.vcs.root:
                    has_vcschild = True
                    if not rootvcs.rootinit and not self._is_targeted(rootvcs.obj):
                        rootvcs.init_root()
                        self.roots.add(rootvcs.path)
                    fileobj.vcsstatus = rootvcs.obj.vcsstatus
                    fileobj.vcsremotestatus = rootvcs.obj.vcsremotestatus
                else:
                    fileobj.vcsstatus = rootvcs.status_subpath(realpath)
                self.redraw = True

        return has_vcschild

    def _queue_process(self):  # pylint: disable=too-many-branches
        """Process queue: Initialize roots under dirobj"""
        dirobjs = []
        paths = set()
        self.roots.clear()

        while True:
            try:
                dirobjs.append(self.queue.get(block=False))
            except queue.Empty:
                break

        for dirobj in dirobjs:
            if dirobj.path in paths:
                continue
            paths.add(dirobj.path)

            if dirobj.vcs.track:
                rootvcs = dirobj.vcs.rootvcs
                if rootvcs.path not in self.roots \
                        and rootvcs.check_outdated() and rootvcs.update_root():
                    rootvcs.update_tree()
                    self.roots.add(rootvcs.path)
                    self.redraw = True

            has_vcschild = self._update_files(dirobj.files_all)

            if dirobj.has_vcschild != has_vcschild:
                dirobj.has_vcschild = has_vcschild
                self.redraw = True

    def run(self):
        while True:
            self.awoken.wait()
            self.awoken.clear()

            self._queue_process()

            if self.redraw:
                self.redraw = False
                for column in self.ui.browser.columns:
                    if column.target and column.target.is_directory:
                        column.need_redraw = True
                self.ui.status.need_redraw = True
                while self._hindered():
                    time.sleep(0.01)
                self.ui.redraw()

    def wakeup(self, dirobj):
        """Wakeup thread"""
        self.queue.put(dirobj)
        self.awoken.set()


# Backend imports
from .bzr import Bzr  # NOQA pylint: disable=wrong-import-position
from .git import Git  # NOQA pylint: disable=wrong-import-position
from .hg import Hg  # NOQA pylint: disable=wrong-import-position
from .svn import SVN  # NOQA pylint: disable=wrong-import-position


class BzrRoot(VcsRoot, Bzr):
    ''' Bzr root '''
    pass


class GitRoot(VcsRoot, Git):
    ''' Git root '''
    pass


class HgRoot(VcsRoot, Hg):
    ''' Hg root '''
    pass


class SVNRoot(VcsRoot, SVN):
    ''' SVN root '''
    pass
