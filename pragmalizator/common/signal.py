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

from twisted.internet import reactor
from pragmalizator.common import log
from pragmalizator import hacks

# define names here to make pyflakes happy, the correct values are set by the
# _reimport_constants() method
python_signal = hacks.import_signal()


# Import explicitly to avoid syntax checkers warnings
ITIMER_PROF = python_signal.ITIMER_PROF
ITIMER_REAL = python_signal.ITIMER_REAL
ITIMER_VIRTUAL = python_signal.ITIMER_VIRTUAL
NSIG = python_signal.NSIG
SIGABRT = python_signal.SIGABRT
SIGALRM = python_signal.SIGALRM
SIGBUS = python_signal.SIGBUS
SIGCHLD = python_signal.SIGCHLD
SIGCLD = python_signal.SIGCLD
SIGCONT = python_signal.SIGCONT
SIGFPE = python_signal.SIGFPE
SIGHUP = python_signal.SIGHUP
SIGILL = python_signal.SIGILL
SIGINT = python_signal.SIGINT
SIGIO = python_signal.SIGIO
SIGIOT = python_signal.SIGIOT
SIGKILL = python_signal.SIGKILL
SIGPIPE = python_signal.SIGPIPE
SIGPOLL = python_signal.SIGPOLL
SIGPROF = python_signal.SIGPROF
SIGPWR = python_signal.SIGPWR
SIGQUIT = python_signal.SIGQUIT
SIGRTMAX = python_signal.SIGRTMAX
SIGRTMIN = python_signal.SIGRTMIN
SIGSEGV = python_signal.SIGSEGV
SIGSTOP = python_signal.SIGSTOP
SIGSYS = python_signal.SIGSYS
SIGTERM = python_signal.SIGTERM
SIGTRAP = python_signal.SIGTRAP
SIGTSTP = python_signal.SIGTSTP
SIGTTIN = python_signal.SIGTTIN
SIGTTOU = python_signal.SIGTTOU
SIGURG = python_signal.SIGURG
SIGUSR1 = python_signal.SIGUSR1
SIGUSR2 = python_signal.SIGUSR2
SIGVTALRM = python_signal.SIGVTALRM
SIGWINCH = python_signal.SIGWINCH
SIGXCPU = python_signal.SIGXCPU
SIGXFSZ = python_signal.SIGXFSZ
SIG_DFL = python_signal.SIG_DFL
SIG_IGN = python_signal.SIG_IGN


def signal(sig, action):
    """
    The point of this module and method is to decouple signal handlers from
    each other. Standard way to deal with handlers is to always store the old
    handler and call it. It creates a chain of handlers, making it impossible
    to later remove the handler.

    This method behaves like signal.signal() from standard python library.
    It always returns SIG_DFL indicating that the new handler is not supposed
    to call the old one.
    """
    assert callable(action), ("Second argument of signal() needs to be a "
                              "callable, got %r instead" % (action, ))
    global _handlers
    _install_handler(sig)

    if action in _handlers[sig]:
        log.debug('signal',
                  "Handler for signal %s already registered. %r", sig, action)
        return SIG_DFL
    _handlers[sig][1].append(action)
    return SIG_DFL


def unregister(sig, action):
    global _handlers

    if sig not in _handlers:
        raise ValueError("We don't have a handler installed for signal %r" %
                         (sig, ))
    _handlers[sig][1].remove(action)


def reset():
    """
    Clear global data and remove the handlers.
    CAUSION! This method sets as a signal handlers the ones which it has
    noticed on initialization time. If there has been another handler installed
    on top of us it will get removed by this method call.
    """
    global _handlers, python_signal
    for sig, (previous, _) in _handlers.iteritems():
        if not previous:
            previous = SIG_DFL
        python_signal.signal(sig, previous)
    _handlers = dict()


### Module private ###

# signal -> (orignal_handler, [callable])
_handlers = dict()


def _install_handler(sig):
    global _handlers, python_signal
    if sig in _handlers:
        # we are already installed for this signal
        return

    current = python_signal.getsignal(sig)
    if current is None or current == SIG_DFL or current == SIG_IGN:
        current = None
    _handlers[sig] = (current, [])
    log.log('signal', "Instaling generic signal handler for signal %r.", sig)
    python_signal.signal(sig, _handler_ext)


def _handler_ext(signum, frame):
    reactor.callFromThread(_handler_int, signum, frame) #@UndefinedVariable


def _handler_int(signum, frame):
    global _handlers

    old_handler, handlers = _handlers[signum]

    for handler in handlers:
        handler(signum, frame)
    if callable(old_handler):
        old_handler(signum, frame)
