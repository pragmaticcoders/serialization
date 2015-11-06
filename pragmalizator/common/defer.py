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
import warnings

from twisted.internet.defer import *
from twisted.internet.defer import (returnValue, passthru, FirstError,
                                    setDebugging, CancelledError, )
from twisted.python import failure

from pragmalizator.common import log, decorator, error, time

from pragmalizator.interface.log import LogLevel
from pragmalizator.interface.fiber import IFiber


def drop_result(_result, _method, *args, **kwargs):
    warnings.warn("defer.drop_result() is deprecated, "
                  "please use defer.drop_param()",
                  DeprecationWarning)
    assert callable(_method), "method %r is not callable" % (_method, )
    return _method(*args, **kwargs)


def bridge_result(_result, _method, *args, **kwargs):
    warnings.warn("defer.bridge_result() is deprecated, "
                  "please use defer.bridge_param()",
                  DeprecationWarning)
    assert callable(_method), "method %r is not callable" % (_method, )
    d = maybeDeferred(_method, *args, **kwargs)
    d.addCallback(override_result, _result)
    return d


def drop_param(_param, _method, *args, **kwargs):
    assert callable(_method), "method %r is not callable" % (_method, )
    return _method(*args, **kwargs)


def bridge_param(_param, _method, *args, **kwargs):
    assert callable(_method), "method %r is not callable" % (_method, )
    d = maybeDeferred(_method, *args, **kwargs)
    d.addCallback(override_result, _param)
    return d


def keep_param(_param, _method, *args, **kwargs):
    assert callable(_method), "method %r is not callable" % (_method, )
    d = maybeDeferred(_method, _param, *args, **kwargs)
    d.addCallback(override_result, _param)
    return d


def call_param(_param, _attr_name, *args, **kwargs):
    _method = getattr(_param, _attr_name, None)
    assert _method is not None, \
           "%r does not have attribute %s" % (_param, _attr_name, )
    assert callable(_method), "method %r is not callable" % (_method, )
    return _method(*args, **kwargs)


def inject_param(_param, _index, _method, *args, **kwargs):
    assert callable(_method), "method %r is not callable" % (_method, )
    args = args[:_index] + (_param, ) + args[_index:]
    return _method(*args, **kwargs)


def override_result(_param, _result):
    return _result


def handle_failure(failure, message, logger=None):
    error.handle_failure(logger, failure, message)


def raise_error(_param, _error_type, *args, **kwargs):
    raise _error_type(*args, **kwargs)


def print_debug(_param, _template="", *args):
    print _template % args
    return _param


def print_trace(_param, _template="", *args):
    postfix = repr(_param)
    if isinstance(_param, failure.Failure):
        postfix = "%r %s" % (_param, error.get_failure_message(_param))
    prefix = _template % args
    prefix = prefix + ": " if prefix else prefix
    print "%s%s" % (prefix, postfix)
    return _param


def debug(_param, _template="", *args):
    log.logex("trace", LogLevel.debug, _template, args)
    return _param


def trace(_param, _template="", *args):
    postfix = repr(_param)
    if isinstance(_param, failure.Failure):
        postfix = "%r %s" % (_param, error.get_failure_message(_param))
    prefix = _template % args
    prefix = prefix + ": " if prefix else prefix
    message = "%s%s" % (prefix, postfix)
    log.logex("trace", LogLevel.debug, message)
    return _param


def maybeDeferred(f, *args, **kw):
    """
    Copied from twsited.internet.defer and add a check to detect fibers.
    """
    try:
        result = f(*args, **kw)
    except Exception:
        return fail(failure.Failure())

    if IFiber.providedBy(result):
        import traceback
        frames = traceback.extract_stack()
        msg = "%s returned a fiber instead of a deferred" % (f, )
        if len(frames) > 1:
            msg += "; called from %s" % (frames[-2], )
        raise RuntimeError(msg)

    if isinstance(result, Deferred):
        return result
    elif isinstance(result, failure.Failure):
        return fail(result)
    else:
        return succeed(result)


def join(*values):
    """
    @param values: the list of value that could contain deferred
                      that result should be returned.
    @type values: list of defer.Deferred
    @return: a defer.Deferred fired with a list containing the values
             where the deferreds have been replaced by there callback values.
             of the specified defer.Deferred whose succeed, the failures
             are swallowed silently so they should be handled by the caller
             if something should be done with them.
    @rtype: defer.Deferred
    @callback: list of object
    """

    def wrap_value(value):
        if isinstance(value, Deferred):
            return value
        return succeed(value)

    def filter_result(param):
        return [result for success, result in param if success]

    deferreds = [wrap_value(v) for v in values]
    dl = DeferredList(deferreds, consumeErrors=True)
    dl.addCallback(filter_result)
    return dl


@decorator.simple_function
def ensure_async(function_original):
    """
    A function decorated with this will always return a defer.Deferred
    even when returning synchronous result or raise an exception.
    """

    def wrapper(*args, **kwargs):
        try:
            result = function_original(*args, **kwargs)
            if isinstance(result, Deferred):
                return result
            d = Deferred()
            d.callback(result)
            return d
        except:
            return fail()

    return wrapper


class Notifier(object):

    def __init__(self):
        self._notifications = {}

    def wait(self, notification):
        d = Deferred(self._remove_deferred)
        self._store(notification, d)
        return d

    def cancel(self, notification):
        notifications = self._pop(notification)
        if notifications:
            for d in notifications:
                d.cancel()

    def callback(self, notification, result):
        notifications = self._pop(notification)
        if notifications:
            for d in notifications:
                d.callback(result)

    def errback(self, notification, failure):
        notifications = self._pop(notification)
        if notifications:
            for d in notifications:
                d.errback(failure)

    def _store(self, notification, d):
        if notification not in self._notifications:
            self._notifications[notification] = []
        self._notifications[notification].append(d)

    def _remove_deferred(self, d):
        for list_for_notification in self._notifications.values():
            if d in list_for_notification:
                list_for_notification.remove(d)

    def _pop(self, notification):
        if notification in self._notifications:
            return self._notifications.pop(notification)


class TimeoutError(Exception):
    pass


class Timeout(DeferredList):

    def __init__(self, timeout, deferred, message="Timeout expired"):
        self._master = deferred
        self._control = Deferred()

        self._call_later = time.call_later(
            timeout, self._control.errback, TimeoutError(message))

        DeferredList.__init__(self,
                              [self._master, self._control],
                              fireOnOneCallback=True,
                              fireOnOneErrback=True,
                              consumeErrors=True)
        self.addCallbacks(self._callback, self._errback)

    def _callback(self, result):
        self.cancel()
        return result[0]

    def _errback(self, fail):
        if fail.check(FirstError):
            fail = fail.value.subFailure
        self.cancel()
        return fail

    def cancel(self):
        if self._call_later.active():
            self._call_later.cancel()
        self._master.cancel()
        self._control.cancel()
