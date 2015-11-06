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
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
import sys

from zope.interface import implements

from pragmalizator import hacks
from pragmalizator.common import log


def scale(factor):
    '''
    Scale time by the factor.
    @param factor: Factor to scale.
                   Values greater than 1 makes time pass slower.
                   Values from range 0:1 makes time pass faster.
    @type factor: C{float}
    '''
    assert 0 < factor, "%d is not greater than 0" % (factor, )
    global _time_scale
    _time_scale = float(factor) * _debugger_scale()


def time():
    '''
    Get current time.
    @return: Currect time in seconds from Epoch taking into acount the
             time scaling mechanism.
    @rtype: float
    '''
    return time_no_sfx()


def future(seconds):
    '''
    Get time in future being aware of time scalling mechanism.
    @param seconds: How many seconds from now
    @type seconds: C{float}
    @return: Time in seconds from Epoch seconds from now.
    @rtype: C{float}
    '''
    return time() + seconds


def left(moment):
    '''
    How much time is left until the specified time in future, taking into
    account time scaling.

    @param moment: Time in number of scaled seconds since Epoc
    @type moment:  C{float}

    @return: Time in real seconds left.
    @rtype:  C{float}
    '''
    return (moment - time())


def callLater(_seconds, _f, *args, **kwargs):
    return call_later(_seconds, _f, *args, **kwargs)


def call_next(_f, *args, **kwargs):
    return call_later(0, _f, *args, **kwargs)


def call_later(_seconds, _f, *args, **kwargs):
    '''
    Wrapper for reactor.callLater() aware the time scalling.
    This method should always be used instead directly touching the reactor.
    See: L{twisted.internet.interfaces.IDelayedCall.callLater}.
    '''
    cur_scale = _get_scale()
    if cur_scale == 1:
        return reactor.callLater(_seconds, _f, #@UndefinedVariable
                                 *args, **kwargs)
    else:
        _seconds = _seconds * cur_scale
        call = reactor.callLater(_seconds, _f, #@UndefinedVariable
                                 *args, **kwargs)
        return ScaledDelayedCall(cur_scale, call)


def reset():
    '''
    Reset any manipulations done by the module.
    '''
    global _time_scale
    _time_scale = 1


### private ###

_time_scale = None
_python_time = hacks.import_time()
clock = _python_time.clock
sleep = _python_time.sleep
strftime = _python_time.strftime
localtime = _python_time.localtime


def _get_scale():
    global _time_scale
    return _time_scale


class ScaledDelayedCall(object):
    implements(IDelayedCall)

    def __init__(self, scale, call):
        self._scale = scale
        self._call = call

    ### IDelayedCall ###

    def getTime(self):
        return self._call.getTime() / self._scale

    def cancel(self):
        return self._call.cancel()

    def delay(self, secondsLater):
        return self._call.delay(secondsLater * self._scale)

    def reset(self, secondsFromNow):
        return self._call.reset(secondsFromNow * self._scale)

    def active(self):
        return self._call.active()


def _debugger_scale():
    if sys.gettrace() is None:
        return 1
    else:
        return 4


reset()
