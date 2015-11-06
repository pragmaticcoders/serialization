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
from zope.interface import Interface, Attribute

from pragmalizator.common import enum

__all__ = ["TriggerType", "FiberError",
           "FiberStartupError", "FiberTriggerError",
           "FiberCancelled", "IFiberDescriptor", "IFiber",
           "ICancellable"]


class TriggerType(enum.Enum):
    '''Type of fiber triggering:

      - succeed:   Execution starts by the callback part of the chain.
      - fail:      Execution starts by the errback part of the chain.
    '''

    succeed, fail = range(2)


class FiberError(Exception):
    pass


class FiberStartupError(FiberError):
    pass


class FiberTriggerError(FiberError):
    pass


class FiberCancelled(Exception):
    pass


class WovenSection(Interface):

    state = Attribute("Fiber section state")
    descriptor = Attribute("L{IFiberDescriptor}")

    def enter():
        '''Initializes a woven section that will allow all functions
        called from the caller to use fiber-aware functions.'''

    def abort(result=None):
        '''Exits a woven section without starting any fibers.
        Returns None.'''

    def exit(result=None):
        '''Exits a woven section. Root sections return a deferred
        called when all fibers have been executed, and sub-sections
        return the result as-is.'''


class IFiberDescriptor(Interface):

    fiber_id = Attribute("Fiber identifier, same for all nested fibers")
    fiber_depth = Attribute("Depth in the fiber chain")

    def attach(fiber):
        '''Attaches a fiber to the descriptor.
        It will call the fiber method bind().'''


class IFiber(IFiberDescriptor):
    '''Fibers are used to specify a chain of asynchronous execution.

    The use case is to specify a chain, return it and delegate
    the responsibility of starting it to the caller.

    Fibers can be nested to follow the string of execution.
    Nested fibers have the same fiber identifier but sub-fibers
    have its depth incremented.

    Fiber serialization format::

        (TRIGGER_TYPE, INITAL_PARAM, [((CB_IDENTIFIER, CB_ARGS, CALL_KWARGSS),
                                       (EB_IDENTIFIER, EB_ARGS, EB_KWARGSS))])

    Example::

        > f = Fiber()
        > f.addCallback(add, 5)
        > f.addErrback(resolve_error)
        > f.addCallbacks(success, failed,
                         callbackArgs=(42,),
                         callbackKeywords={"spam": "beans"},
                         errbackKeywords={"bacon", "eggs"})
        > f.suceed(0)

    Serialize to::

        (TriggerType.succeed, 0,
         [(("add", (5,), None), None),
          (None, ("resolve_error", None, None)),
          (("success", (42,), {"spam": "beans"}),
           ("failed", None, {"bacon", "eggs"}))])

    '''

    def start():
        '''Start the fiber asynchronous execution.
        Should theoretically not be called by the creator of the fiber,
        but by the parent fiber descriptor.
        Because parent fiber descriptor can be a fiber itself,
        '''

    def trigger(trigger_type, param=None):
        '''Trigger the fiber given a trigger type.'''

    def succeed(param=None):
        '''Set the fiber to start on the callback path
        with the specified parameter.
        Same as calling trigger(TriggerType.succeed, param).'''

    def fail(param=None):
        '''Set the fiber to start on the errback path
        with the specified parameter.
        Same as calling trigger(TriggerType.fail, failure).'''

    def chain(fiber):
        '''Chains the specified fiber.
        Like adding all the callback of the specified fiber.
        The Chained fiber will be considerred triggered.'''

    def addCallbacks(callback, errback=None,
                     callbackArgs=None, callbackKeywords=None,
                     errbackArgs=None, errbackKeywords=None):
        pass

    def addCallback(callback, *args, **kwargs):
        pass

    def addErrback(errback, *args, **kwargs):
        pass

    def addBoth(callback, *args, **kwargs):
        pass


class ICancellable(Interface):

    def is_active():
        '''Returns status of the fiber, cancelled or not'''
