# F3AT - Flumotion Asynchronous Autonomous Agent Toolkit
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# See "LICENSE.GPL" in the source distribution for more information.

# Headers in this file shall remain intact.

import errno
import os
import sys
import time

from pragmalizator.common import log


PROCESS_TYPE = "pragmalizator"


def acquire_pidfile(rundir, process_type=PROCESS_TYPE, name=None):
    """
    Open a PID file for writing, using the given process type and
    process name for the filename. The returned file can be then passed
    to writePidFile after forking.

    @rtype:   str
    @returns: file object, open for writing
    """
    from pragmalizator.common.run import get_pidpath
    _ensure_dir(rundir, "rundir")
    path = get_pidpath(rundir, process_type, name)
    return open(path, 'w')


def write_pidfile(rundir, process_type=PROCESS_TYPE,
                  name=None, file=None): #@ReservedAssignment
    """
    Write a pid file in the run directory, using the given process type
    and process name for the filename.

    @rtype:   str
    @returns: full path to the pid file that was written
    """
    from pragmalizator.common.run import get_pidpath
    # don't shadow builtin file
    pid_file = file
    if pid_file is None:
        _ensure_dir(rundir, "rundir")
        filename = get_pidpath(rundir, process_type, name)
        pid_file = open(filename, 'w')
    else:
        filename = pid_file.name
    pid_file.write("%d\n" % (os.getpid(), ))
    pid_file.close()
    os.chmod(filename, 0644)
    return filename


def delete_pidfile(rundir, process_type=PROCESS_TYPE, name=None, force=False):
    """
    Delete the pid file in the run directory, using the given process type
    and process name for the filename.

    @param force: if errors due to the file not existing should be ignored
    @type  force: bool

    @rtype:   str
    @returns: full path to the pid file that was written
    """
    from pragmalizator.common.run import get_pidpath
    log.debug(process_type, 'deleting pid file')
    path = get_pidpath(rundir, process_type, name)
    try:
        os.unlink(path)
    except OSError, e:
        if e.errno == errno.ENOENT and force:
            pass
        else:
            raise
    return path


def wait_pidfile(rundir, process_type=PROCESS_TYPE, name=None):
    """
    Wait for the given process type and name to have started and created
    a pid file.

    Return the pid.
    """
    from pragmalizator.common.run import get_pid
    # getting it from the start avoids an unneeded time.sleep
    pid = get_pid(rundir, process_type, name)

    while not pid:
        time.sleep(0.1)
        pid = get_pid(rundir, process_type, name)

    return pid


def wait_for_term():
    """
    Wait until we get killed by a TERM signal (from someone else).
    """

    class Waiter:

        def __init__(self):
            self.sleeping = True
            import signal
            self.oldhandler = signal.signal(signal.SIGTERM,
                                            self._SIGTERMHandler)

        def _SIGTERMHandler(self, number, frame):
            self.sleeping = False

        def sleep(self):
            while self.sleeping:
                time.sleep(0.1)

    waiter = Waiter()
    waiter.sleep()


def _ensure_dir(directory, description):
    """
    Ensure the given directory exists, creating it if not.

    @raise errors.FatalError: if the directory could not be created.
    """
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except OSError, e:
            sys.stderr.write("could not create %s directory %s: %s" % (
                             description, directory, str(e)))
