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

from _noarch_run import *


DEFAULT_RUN_DIR = "/tmp"


def _describe(processName, processType):
    if not processName:
        return processType
    if not processType:
        return processName
    return "%s %s" % (processType, processName)


def status(processName, rundir=DEFAULT_RUN_DIR, process_type=PROCESS_TYPE):
    pid = get_pid(rundir, process_type, processName)
    if not pid:
        print "%s is not running" % _describe(process_type, processName)
        return
    if check_pid_running(pid):
        print "%s is running with pid %d" % (
            _describe(process_type, processName), pid)
    else:
        print "%s is dead (stale pid %d)" % (
            _describe(process_type, processName), pid)
        sys.exit(3)


def stop(processName, rundir='/tmp', process_type=PROCESS_TYPE):
    pid = get_pid(rundir, process_type, processName)
    if not pid:
        print "%s is not running" % _describe(process_type, processName)
        return
    startClock = time.clock()
    termClock = startClock + 20
    killClock = termClock + 10

    log.debug("run", 'stopping process with pid %d', pid)
    if not term_pid(pid):
        log.warning("run", 'No process with pid %d', pid)
        return  1

    # wait for the kill
    while (check_pid_running(pid)):
        if time.clock() > termClock:
            log.warning("run", "Process with pid %d has not responded "
                        "to TERM for %d seconds, killing", pid, 20)
            kill_pid(pid)
            # so it does not get triggered again
            termClock = killClock + 1.0

        if time.clock() > killClock:
            log.warning("run", "Process with pid %d has not responded to "
                        "KILL for %d seconds, stopping", pid, 10)
            return 1
    print "%s with pid %d stopped" % (
            _describe(process_type, processName), pid)
    return 0


is_already_daemon = False


def daemonize(stdin=os.devnull, stdout=os.devnull, stderr=os.devnull):
    '''
    This forks the current process into a daemon.
    The stdin, stdout, and stderr arguments are file names that
    will be opened and be used to replace the standard file descriptors
    in sys.stdin, sys.stdout, and sys.stderr.
    These arguments are optional and default to /dev/null.

    The fork will switch to the given directory.

    Used by external projects (ft).
    '''
    # Redirect standard file descriptors.
    si = open(stdin, 'r')
    os.dup2(si.fileno(), sys.stdin.fileno())
    try:
        log.FluLogKeeper.redirect_to(stdout, stderr)
    except IOError, e:
        if e.errno == errno.EACCES:
            sys.stderr.write('Permission denied writing to log file %s.' %\
                             e.filename)

    global is_already_daemon
    if is_already_daemon:
        return

    # first fork
    _fork()
    # do second fork
    _fork()
    # Now I am a daemon!
    # don't add stuff here that can fail, because from now on the program
    # will keep running regardless of tracebacks
    is_already_daemon = True


def get_pid(rundir, process_type=PROCESS_TYPE, name=None):
    """
    Get the pid from the pid file in the run directory, using the given
    process type and process name for the filename.

    @returns: pid of the process, or None if not running or file not found.
    """
    pidPath = get_pidpath(rundir, process_type, name)
    log.log('run', 'pidfile for %s %s is %s' % (process_type, name, pidPath))

    if not os.path.exists(pidPath):
        return

    pidFile = open(pidPath, 'r')
    pid = pidFile.readline()
    pidFile.close()
    if not pid or int(pid) == 0:
        return

    return int(pid)


def signal_pid(pid, signum):
    """
    Send the given process a signal.

    @returns: whether or not the process with the given pid was running
    """
    try:
        os.kill(pid, signum)
        return True
    except OSError, e:
        # see man 2 kill
        if e.errno == errno.EPERM:
            # exists but belongs to a different user
            return True
        if e.errno == errno.ESRCH:
            # pid does not exist
            return False
        raise


def term_pid(pid):
    """
    Send the given process a TERM signal.

    @returns: whether or not the process with the given pid was running
    """
    from pragmalizator.common import signal
    return signal_pid(pid, signal.SIGTERM)


def kill_pid(pid):
    """
    Send the given process a KILL signal.

    @returns: whether or not the process with the given pid was running
    """
    from pragmalizator.common import signal
    return signal_pid(pid, signal.SIGKILL)


def check_pid_running(pid):
    """
    Check if the given pid is currently running.

    @returns: whether or not a process with that pid is active.
    """
    return signal_pid(pid, 0)


def wait_pidfile(rundir, process_type=PROCESS_TYPE, name=None):
    """
    Wait for the given process type and name to have started and created
    a pid file.

    Return the pid.
    """
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
            import signal #@Reimport
            self.oldhandler = signal.signal(signal.SIGTERM,
                                            self._SIGTERMHandler)

        def _SIGTERMHandler(self, number, frame):
            self.sleeping = False

        def sleep(self):
            while self.sleeping:
                time.sleep(0.1)

    waiter = Waiter()
    waiter.sleep()


def get_pidpath(rundir, process_type, name=None):
    """
    Get the full path to the pid file for the given process type and name.
    """
    assert rundir, "rundir is not configured"
    path = os.path.join(rundir, '%s.pid' % process_type)
    if name:
        path = os.path.join(rundir, '%s.%s.pid' % (process_type, name))
    log.log('common', 'get_pidpath for type %s, name %r: %s'
            % (process_type, name, path))
    return path


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


def _fork():
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError, e:
        sys.stderr.write("Failed to fork: (%d) %s\n" % (e.errno, e.strerror))
        sys.exit(1)
