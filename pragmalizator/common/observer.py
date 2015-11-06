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
from zope.interface import implements

from pragmalizator.common import fiber, defer

from pragmalizator.interface.observer import *
from pragmalizator.interface.serialization import *


class Observer(object):
    '''
    I observe the fiber returned by a callable and remember its result.
    I also expose methods to wait for the fiber to finish, and get its state.
    '''
    implements(IObserver, ISerializable)

    def __init__(self, _method, *args, **kwargs):

        if not callable(_method):
            raise TypeError(
                "1st argument of __init__ should be a callable, got %r" %
                (type(_method), ))

        self._method = _method
        self._args = args
        self._kwargs = kwargs

        self._result = None
        self._finished = False
        self._failed = False

        self._notifier = defer.Notifier()

    def initiate(self):
        d = fiber.maybe_fiber(self._method, *self._args, **self._kwargs)
        d.addCallbacks(self._finished_cb, self._failed_cb)

        # Unreference everything we don't need anymore
        self._method = None
        self._args = None
        self._kwargs = None

        return d

    ### IObserver ###

    def notify_finish(self):
        if self._failed:
            return defer.fail(self._result)
        elif self._finished:
            return defer.succeed(self._result)
        else:
            return self._notifier.wait('finished')

    def active(self):
        return not self._failed and not self._finished

    def get_result(self):
        if self.active():
            raise RuntimeError(
                'Observer.get_result() called on observer which is not done '
                'yet. Before using this method you should ensure that this '
                'job is done, by calling .active()')
        return self._result

    ### ISerializable ###

    type_name = 'fiber-observer'

    def snapshot(self):
        return None

    def recover(self, snapshot):
        pass

    def restored(self):
        pass

    ### IRestorator ###

    @classmethod
    def prepare(cls):
        return cls.__new__(cls)

    ### private ###

    def _finished_cb(self, result):
        self._finished = True
        self._result = result
        self._notifier.callback('finished', result)
        return result

    def _failed_cb(self, fail):
        self._failed = True
        self._result = fail
        self._notifier.errback('finished', fail)
        fail.raiseException()

    def __eq__(self, other):
        return type(self) == type(other) or NotImplemented

    def __ne__(self, other):
        if type(self) != type(other):
            return NotImplemented
        else:
            return False
