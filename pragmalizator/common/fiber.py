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
import os
import sys
import uuid
import warnings
import traceback
import types

from twisted.python import failure
from zope.interface import implements

from pragmalizator.common import log, error, defer, decorator, text_helper

from pragmalizator.interface.log import LogLevel
from pragmalizator.interface.fiber import (IFiber, FiberError, IFiberDescriptor,
                                  TriggerType, FiberCancelled,
                                  FiberTriggerError, FiberStartupError)
from pragmalizator.interface.serialization import ISnapshotable


SECTION_STATE_TAG = "__fiber_section_dict__"
SECTION_BOUNDARY_TAG = "__section_boundary__"


def drop_result(_result, _method, *args, **kwargs):
    warnings.warn("fiber.drop_result() is deprecated, "
                  "please use fiber.drop_param()",
                  DeprecationWarning)
    assert callable(_method), "method %r is not callable" % (_method, )
    return _method(*args, **kwargs)


def bridge_result(_result, _method, *args, **kwargs):
    warnings.warn("fiber.bridge_result() is deprecated, "
                  "please use fiber.bridge_param()",
                  DeprecationWarning)
    assert callable(_method), "method %r is not callable" % (_method, )
    f = Fiber(debug_depth=1, debug_call=_method)
    f.add_callback(drop_result, _method, *args, **kwargs)
    f.add_callback(override_result, _result)
    return f.succeed()


def drop_param(_param, _method, *args, **kwargs):
    """
    Used as a callback to ignore the result from the previous callback
    added to this fiber.
    """
    assert callable(_method), "method %r is not callable" % (_method, )
    return _method(*args, **kwargs)


def bridge_param(_param, _method, *args, **kwargs):
    """
    Used as a callback to keep the result from the previous callback
    and use that instead of the result of the given callback when
    chaining to the next callback in the fiber.
    """
    assert callable(_method), "method %r is not callable" % (_method, )
    f = Fiber(debug_depth=1, debug_call=_method)
    f.add_callback(drop_param, _method, *args, **kwargs)
    f.add_callback(override_result, _param)
    return f.succeed()


def keep_param(_param, _method, *args, **kwargs):
    assert callable(_method), "method %r is not callable" % (_method, )
    f = Fiber(debug_depth=1, debug_call=_method)
    f.add_callback(_method, *args, **kwargs)
    f.add_callback(override_result, _param)
    return f.succeed(_param)


def call_param(_param, _attr_name, *args, **kwargs):
    _method = getattr(_param, _attr_name, None)
    assert _method is not None, \
           "%r do not have attribute %s" % (_param, _attr_name, )
    assert callable(_method), "method %r is not callable" % (_method, )
    return _method(*args, **kwargs)


def getattr_param(_param, _attr_name):
    return getattr(_param, _attr_name)


def inject_param(_param, _index, _method, *args, **kwargs):
    assert callable(_method), "method %r is not callable" % (_method, )
    args = args[:_index] + (_param, ) + args[_index:]
    return _method(*args, **kwargs)


def override_result(_param, _result):
    return _result


def handle_failure(failure, message, logger=None):
    error.handle_failure(logger, failure, message)


def raise_error(_param, _error_type, *args, **kwargs):
    if issubclass(_error_type, error.FeatError) and 'cause' not in kwargs:
        kwargs['cause'] = _param
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
    log.logex("fiber", LogLevel.debug, _template, args, log_name="debug")
    return _param


def trace(_param, _template="", *args):
    postfix = repr(_param)
    if isinstance(_param, failure.Failure):
        postfix = "%r %s" % (_param, error.get_failure_message(_param))
    prefix = _template % args
    prefix = prefix + ": " if prefix else prefix
    message = "%s%s" % (prefix, postfix)
    log.logex("fiber", LogLevel.debug, message, log_name="trace")
    return _param


def succeed(param=None, canceller=None, debug_depth=0, debug_call=None):
    f = Fiber(canceller, debug_depth=debug_depth+1, debug_call=debug_call)
    return f.succeed(param)


def fail(fail=None, canceller=None, debug_depth=0, debug_call=None):
    if isinstance(fail, error.FeatError) and fail.cause_traceback is None:
        fail.cause_traceback = ''.join(traceback.format_stack()[:-1])
    f = Fiber(canceller, debug_depth=debug_depth+1, debug_call=debug_call)
    return f.fail(fail)


def wrap_defer(_method, *args, **kwargs):
    '''
    Quick way to call a function returning a Deferred from place when you are
    supposed to return the Fiber.
    '''
    return wrap_defer_ex(_method, args, kwargs, debug_depth=1)


def wrap_defer_ex(_method, args=None, kwargs=None, debug_depth=0):
    f = succeed(debug_depth=debug_depth+1, debug_call=_method)
    f.add_callback(drop_param, _method, *(args or ()), **(kwargs or {}))
    return f


def maybe_fiber(_function, *args, **kwargs):
    try:
        result = _function(*args, **kwargs)
    except Exception:
        return defer.fail(failure.Failure())
    else:
        if IFiber.providedBy(result):
            return result.start()
        if isinstance(result, defer.Deferred):
            return result
        elif isinstance(result, failure.Failure):
            return defer.fail(result)
        else:
            return defer.succeed(result)


trace_fiber_calls = os.environ.get("FEAT_TRACE_FIBERS", "NO").upper() \
                    in ("YES", "1", "TRUE")

debug_fibers = os.environ.get("FEAT_DEBUG_FIBERS", "NO").upper() \
               in ("YES", "1", "TRUE")


@decorator.simple_function
def woven(fun):
    '''Decorator that will initialize and eventually start nested fibers.'''

    def wrapper(*args, **kwargs):
        section = WovenSection()
        section.enter()
        result = fun(*args, **kwargs)
        return section.exit(result)

    return wrapper


def get_stack_var(name, depth=0):
    '''This function may fiddle with the locals of the calling function,
    to make it the root function of the fiber. If called from a short-lived
    function be sure to use a bigger frame depth.
    Returns the fiber state or None.'''

    base_frame = _get_base_frame(depth)
    if not base_frame:
        # Frame not found
        raise RuntimeError("Base frame not found")

    # Lookup up the frame stack starting at the base frame for the fiber state
    level = 0
    frame = base_frame
    while frame:
        locals = frame.f_locals
        value = locals.get(name)
        if value is not None:
            if level > 0:
                # Copy a reference of the fiber state in the base frame
                base_frame.f_locals[name] = value
            return value
        if locals.get(SECTION_BOUNDARY_TAG):
            return None
        frame = frame.f_back
        level += 1
    return None


def set_stack_var(name, value, depth=0):
    base_frame = _get_base_frame(depth)
    if not base_frame:
        # Frame not found
        raise RuntimeError("Base frame not found")

    base_frame.f_locals[name] = value


def get_state(depth=0):
    return get_stack_var(SECTION_STATE_TAG, depth=depth+1)


def set_state(state, depth=0):
    set_stack_var(SECTION_STATE_TAG, state, depth=depth+1)


def break_fiber(depth=0):
    """After calling break_fiber, get_state() will return None."""
    set_stack_var(SECTION_BOUNDARY_TAG, True, depth=depth+1)
    set_stack_var(SECTION_STATE_TAG, None, depth=depth+1)


def del_state(depth=0):
    base_frame = _get_base_frame(depth)
    if not base_frame:
        # Frame not found
        raise RuntimeError("Base frame not found")

    locals = base_frame.f_locals
    if SECTION_STATE_TAG in locals:
        del locals[SECTION_STATE_TAG]


def _get_base_frame(depth):
    # Go up the frame stack to the base frame given it's deepness.
    # Go up one level more to account for this function own frame.
    if depth < 0:
        return None
    base_frame = sys._getframe().f_back
    while base_frame and depth >= 0:
        depth -= 1
        base_frame = base_frame.f_back
    return base_frame


class WovenSection(object):
    '''Handles fiber-aware sections.'''

    def __init__(self, descriptor=None):
        self.descriptor = descriptor
        self.state = None
        self._is_root = True
        self._inside = False

    def enter(self):
        if self._inside:
            raise FiberError("Already inside a woven section")
        self._inside = True

        if self.descriptor is None:
            # Use a depth of 1 because we want the state to be
            # in the calling function not in the method.
            state = get_state(depth=1)
            if state is not None:
                # We are in a sub-section, just update the state
                self.state = state
                self.descriptor = state["descriptor"]
                self._is_root = False
                return
            # First woven section, we create an
            # and remember to start the fibers.
            self.descriptor = RootFiberDescriptor()

        state = {"descriptor": self.descriptor}
        set_state(state, depth=1)
        self.state = state

    def abort(self, result=None):
        self._cleanup()

    def exit(self, result=None):
        self._cleanup()

        if not self._is_root:
            # If not a root section just return the result as-is
            return result

        # We are a root sections
        if IFiber.providedBy(result):
            # If the result is a fiber, we initialize and start it
            fiber = IFiber(result)
            self.descriptor.attach(fiber)
            return fiber.start()

        if isinstance(result, defer.Deferred):
            return result
        elif isinstance(result, failure.Failure):
            return defer.fail(result)
        else:
            return defer.succeed(result)

    ### Private Methods ###

    def _cleanup(self):
        if not self._inside:
            raise FiberError("Not inside a woven section")
        self._inside = False
        self.state = None
        if self._is_root:
            del_state(depth=1)


class RootFiberDescriptor(object):
    '''Root fiber descriptor created when get_descriptor()returns None.'''

    implements(IFiberDescriptor)

    fiber_depth = 0

    def __init__(self):
        self.fiber_id = str(uuid.uuid4())

    ### IFiberDescriptor ###

    def attach(self, fiber):
        fiber = IFiber(fiber)
        fiber._bind(self, self.fiber_id, 1)


class FiberInfo(object):

    def __init__(self, stack_depth, called_func):
        self.creator = None
        self.calling = None
        self._init_creator(stack_depth)
        self._init_calling(called_func)

    def _init_creator(self, stack_depth):
        stack = traceback.extract_stack(limit=stack_depth+3)
        entry = stack[0]
        self.creator = "%s:%s:%d" % (os.path.basename(entry[0]),
                                     entry[2], entry[1])

    def _init_calling(self, func):
        if func is None:
            return

        if isinstance(func, types.MethodType):
            func = func.im_func

        if hasattr(func, 'original_func'):
            func = func.original_func

        self.calling = "%s:%s:%d" % (os.path.basename(func.__module__),
                                     func.func_name,
                                     func.func_code.co_firstlineno)


class Fiber(object):
    '''Fibers are used to specify a chain of asynchronous execution.

    Fibers can be nested to follow the string of execution.
    Nested fibers have the same fiber_id but sub-fibers
    have there fiber_depth incremented.

    When chaining fibers, the chained fiber cannot be started anymore.
    If a chained fiber is not triggered, it will start in function
    of the result and state of the master fiber at the point of chaining.

    Examples 1::

      def show(result, header):
          print header, result
          return result

      f1 = Fiber()
      f1.callback(show, "Fiber 1:")
      f1.succeed("F1")

      f2 = Fiber()
      f2.callback(show, "Fiber 2:")
      f2.succeed("F2") # f2 IS triggered

      f1.chain(f2)

      f1.start()

      >> Fiber 1: F1
      >> Fiber 2: F2

    Examples 2::

      def show(result, header):
          print header, result
          return result

      f1 = Fiber()
      f1.callback(show, "Fiber 1:")
      f1.succeed("F1")

      f2 = Fiber()
      f2.callback(show, "Fiber 2:")
      # f2 IS NOT triggered

      f1.chain(f2)

      f1.start()

      >> Fiber 1: F1
      >> Fiber 2: F1

    '''

    implements(IFiber, ISnapshotable)

    def __init__(self, canceller = None, debug_depth=0, debug_call=None):

        self._descriptor = None
        self.fiber_depth = None
        self.fiber_id = None

        self._delegated_startup = False
        self._started = False
        self._trigger = None
        self._param = None

        # [(callable, tuple or None, dict or None,
        #   callable, tuple or None, dict or None)
        #  |Fiber]
        self._calls = []
        self.canceller = canceller
        self.debug = None

        if debug_fibers:
            self.debug = FiberInfo(debug_depth+1, debug_call)

    @property
    def trigger_type(self):
        return self._trigger

    @property
    def trigger_param(self):
        return self._param

    ### serialization.ISnapshotable Methods ###

    def snapshot(self):
        return self._trigger, self._param, self._snapshot_callbacks()

    ### IFiberDescriptor ###

    def attach(self, fiber):
        assert isinstance(fiber, Fiber)
        fiber._bind(self, self.fiber_id, self.fiber_depth + 1)

    ### IFiber Methods ###

    def start(self):
        # Check not started
        self._check_not_started()

        # More checks
        if self._delegated_startup:
            raise FiberStartupError("Fiber with delegated startup cannot "
                                    "be started directly"
                                    + self._get_debug_info())
        if self._trigger is None:
            raise FiberTriggerError("Cannot start a fiber without trigger"
                                    + self._get_debug_info())

        # Ensure there is a descriptor set
        self._ensure_descriptor()

        # Prepare the deferred calls
        d = self._prepare(defer.Deferred())

        # Trigger the deferred
        return self._fire(d, self._trigger, self._param)

    def trigger(self, trigger_type, param=None):
        self._check_not_started()

        if self._delegated_startup:
            raise FiberTriggerError("Fiber with delegated startup cannot "
                                    "change it's trigger anymore"
                                    + self._get_debug_info())
        if self._trigger is not None:
            raise FiberTriggerError("Fiber already triggered"
                                    + self._get_debug_info())

        self._trigger = TriggerType(trigger_type)
        if self._trigger == TriggerType.fail and param is None:
            self._param = failure.Failure()
        else:
            self._param = param
        return self

    def succeed(self, param=None):
        return self.trigger(TriggerType.succeed, param)

    def fail(self, failure=None):
        return self.trigger(TriggerType.fail, failure)

    def chain(self, fiber):
        self._check_not_started()

        assert isinstance(fiber, Fiber)
        fiber._make_delegated()
        self._calls.append(fiber)
        return self

    def add_callbacks(self, callback=None, errback=None,
                      cbargs=None, cbkws=None,
                      ebargs=None, ebkws=None):
        self._check_not_started()

        record = (callback, errback, cbargs, cbkws, ebargs, ebkws)

        self._calls.append(record)

        return self

    def add_callback(self, callback, *args, **kwargs):
        return self.add_callbacks(callback, cbargs=args, cbkws=kwargs)

    def add_errback(self, errback, *args, **kwargs):
        return self.add_callbacks(errback=errback, ebargs=args, ebkws=kwargs)

    def add_both(self, callback, *args, **kwargs):
        return self.add_callbacks(callback, callback,
                                  cbargs=args, cbkws=kwargs,
                                  ebargs=args, ebkws=kwargs)

    ### Protected Methods, called only by other instances of Fiber ###

    def _bind(self, desc, fiber_id, fiber_depth):
        if self._descriptor is not None:
            if self._descriptor == desc:
                # Already attached
                return False
            raise FiberError("Fiber already attached to another descriptor"
                             + self._get_debug_info())

        self._descriptor = desc
        self.fiber_id = fiber_id
        self.fiber_depth = fiber_depth
        return True

    def _make_delegated(self):
        self._delegated_startup = True

    def _snapshot_callbacks(self):
        result = []
        for record in self._calls:
            if isinstance(record, tuple):
                cb, eb, cba, cbk, eba, ebk = record
                dump = self._serialize_callbacks(cb, eb, cba, cbk, eba, ebk)
                result.append(dump)
            else:
                result.extend(record._snapshot_callbacks())
        return result

    def _ensure_descriptor(self):
        descriptor = None
        if self.fiber_id is None:
            # If not attached, creates a root descriptor and attach it.
            # Useful to use fiber directly without decorators.
            descriptor = RootFiberDescriptor()
            descriptor.attach(self)

    def _check_not_started(self):
        if self._started:
            raise FiberStartupError("Fiber already started"
                                    + self._get_debug_info())

    def _prepare(self, d):
        self._started = True

        for record in self._calls:
            if isinstance(record, tuple):
                cb, eb, cba, cbk, eba, ebk = record
                # Wrap the callbacks
                cb, cba, cbk = self._wrap_callback(cb, cba, cbk)
                eb, eba, ebk = self._wrap_callback(eb, eba, ebk)
                # Add the callbacks
                d.addCallbacks(cb, eb, cba, cbk, eba, ebk)
            else:
                # If the chained fiber have been triggered, it will start
                # with the triggered type and param, otherwise it will
                # be started in function of the result of the parent fiber.
                ct = record.trigger_type
                cp = record.trigger_param
                # Prepare the deferred chain to be started
                # at the chaining point
                cd = record._prepare(defer.Deferred())
                d.addCallbacks(self._on_chain_cb, self._on_chain_cb,
                               callbackArgs=(ct, cp, cd, TriggerType.succeed),
                               errbackArgs=(ct, cp, cd, TriggerType.fail))

        return d

    def _fire(self, d, trigger, param=None,
              default_trigger=None, default_param=None):
        if trigger is None:
            trigger = default_trigger
            param = default_param

        if trigger == TriggerType.succeed:
            d.callback(param)
        elif trigger == TriggerType.fail:
            d.errback(param)

        return d

    ### Private Methods ###

    def _get_debug_info(self):
        if self.debug is None:
            return ""
        result = []
        if self.debug.creator:
            result.append("created by %s" % self.debug.creator)
        if self.debug.calling:
            result.append("calling %s" % self.debug.calling)
        return " (%s)" % ("; ".join(result), )

    def _wrap_callback(self, callback, args, kwargs):
        if callback:
            args = (self, callback, args or (), kwargs or {})
            return self._callback_wrapper, args, None
        # Deferred always need a callback, use pass through if not set
        return defer.passthru, None, None

    def _callback_wrapper(self, param, fiber, callback, args, kwargs):
        global trace_fiber_calls
        if trace_fiber_calls:
            self._trace(param, callback, *args, **kwargs)

        if isinstance(param, failure.Failure) and param.check(FiberCancelled):
            param.raiseException()

        if self.canceller and not self.canceller.is_active():
            raise FiberCancelled("Fiber cancelled"
                                 + self._get_debug_info())

        section = WovenSection(descriptor=fiber)
        section.enter()
        try:
            result = callback(param, *args, **kwargs)
        except Exception, e:
            section.abort()
            if debug_fibers:
                e.args = (e.args[0] + self._get_debug_info(), ) + e.args[1:]
            raise
        else:
            return section.exit(result)

    def _serialize_callbacks(self, cb, eb, cba, cbk, eba, ebk):
        # FIXME: Should we deep clone ?
        cbd = None
        ebd = None
        if cb is not None:
            cbd = (cb, cba or None, cbk or None)
        if eb is not None:
            ebd = (eb, eba or None, ebk or None)
        return (cbd, ebd)

    def _on_chain_cb(self, parent_param, trigger, param, d, default_trigger):
        return self._fire(d, trigger, param, default_trigger, parent_param)

    def _trace(self, _param, _method, *args, **kwargs):
        trace_fun = self._trace_lookup.get(_method, Fiber._trace_default)
        trace_fun(self, _param, _method, *args, **kwargs)

    def _trace_default(self, _param, _method, *args, **kwargs):
        args = (_param, ) + args
        return self._trace_call(_method, *args, **kwargs)

    def _trace_drop_param(self, _param, _, _method, *args, **kwargs):
        return self._trace_call(_method, *args, **kwargs)

    def _trace_bridge_param(self, _param, _, _method, *args, **kwargs):
        return self._trace_call(_method, *args, **kwargs)

    def _trace_call_param(self, _param, _, _attr_name, *args, **kwargs):
        _method = getattr(_param, _attr_name, None)
        if _method:
            return self._trace_call(_method, *args, **kwargs)

    def _trace_inject_param(self, _param, _, _index, _method, *args, **kwargs):
        args = args[:_index] + (_param, ) + args[_index:]
        return self._trace_call(_method, *args, **kwargs)

    def _trace_ignore(self, *args, **kwargs):
        return

    def _trace_call(self, _method, *args, **kwargs):
        try:
            file_path = _method.__code__.co_filename
            line_num = _method.__code__.co_firstlineno
        except AttributeError:
            file_path = "unknown"
            line_num = 0

        text = text_helper.format_call(_method, *args, **kwargs)
        log_name = self.fiber_id[:27] + "..."
        log.logex("fiber", LogLevel.log, text, log_name=log_name,
                  file_path=file_path, line_num=line_num)

    _trace_lookup = {drop_result: _trace_drop_param,
                     drop_param: _trace_drop_param,
                     bridge_result: _trace_bridge_param,
                     bridge_param: _trace_bridge_param,
                     call_param: _trace_call_param,
                     inject_param: _trace_inject_param,
                     override_result: _trace_ignore,
                     print_debug: _trace_ignore,
                     print_trace: _trace_ignore,
                     debug: _trace_ignore,
                     trace: _trace_ignore}


class FiberList(Fiber):
    '''List of fiber.
    Created with an iterator over instances implementing L{IFiber}.

    By default, the result passed to the first callback is a list of tuple
    (SUCCESS, VALUE) where SUCCESS is a bool anv VALUE is a fiber result
    if SUCCESS is True or a Failure instance if SUCCESS is False.

    Constructor parameters can alter this behaviour:

     -  if fireOnOneCallback is True, the first fiber returning a value
        will fire the FiberList execution with parameter a tuple with
        the value and the index of the fiber the result comes from.

     -  if fireOnOneErrback is True, the first fiber returning a failure
        will fire the FiberList errback with a L{defer.FirstError}.

    If sub-fibers are not triggered, they will be started in function
    of the state and result of the master fiber.

    Example:

          def show(result, header):
          print header, result
          return result

          f1 = Fiber()
          f1.addCallback(show, "Fiber 1:")
          f1.succeed("F1") # f1 IS triggered

          f2 = Fiber()
          f2.addCallback(show, "Fiber 2:")
          # f2 IS NOT triggered

          fl = FiberList([f1, f2])
          fl.succeed("FL")

          >> Fiber 1: F1
          >> Fiber 2: FL
    '''

    implements(IFiber, ISnapshotable)

    def __init__(self, fibers, fireOnOneCallback=False,
                 fireOnOneErrback=False, consumeErrors=False):
        """Initialize a FiberList.

        @param fibers: an iterator over a collection of L{IFiber}.
        @type fibers:  iterable
        @param fireOnOneCallback: a flag indicating that only one callback
                                  needs to be fired for me to call my callback
        @param fireOnOneErrback: a flag indicating that only one errback needs
                                 to be fired for me to call my errback
        @param consumeErrors: a flag indicating that any errors raised
                              in the original fibers should be consumed
                              by this FiberList.  This is useful to prevent
                              spurious warnings being logged.
        """
        Fiber.__init__(self)
        self._fibers = list(fibers)
        self._fire_on_first_cb = fireOnOneCallback
        self._fire_on_first_eb = fireOnOneErrback
        self._consume_errors = consumeErrors

    ### serialization.ISnapshotable Methods ###

    def snapshot(self):
        return (self.trigger_type, self.trigger_param,
                [f.snapshot() for f in self._fibers])

    ### Protected Methods, called only by other instances of Fiber ###

    def _bind(self, desc, fiber_id, fiber_depth):
        # Bind sub fibers
        if Fiber._bind(self, desc, fiber_id, fiber_depth):
            for f in self._fibers:
                f._bind(desc, fiber_id, fiber_depth)
            return True
        return False

    def _prepare(self, d):
        self._started = True

        items = []

        # Start all fibers with there own Deferred and
        for fiber in self._fibers:
            # Check the fiber is not started
            fiber._check_not_started()
            # Prepare the deferred chain to be started when
            # the deferred specified as parameter is started
            fd = fiber._prepare(defer.Deferred())
            item = (fiber.trigger_type, fiber.trigger_param, fd)
            items.append(item)

        fld = Fiber._prepare(self, defer.Deferred())

        return d.addCallbacks(self._on_callback, self._on_callback,
                              callbackArgs=(items, fld, TriggerType.succeed),
                              errbackArgs=(items, fld, TriggerType.fail))

    ### Private Methods ###

    def _on_callback(self, parent_param, items, fld, default_trigger):
        deferreds= []

        for trigger, param, d in items:
            deferreds.append(d)
            self._fire(d, trigger, param, default_trigger, parent_param)

        dl = defer.DeferredList(deferreds,
                                fireOnOneCallback=self._fire_on_first_cb,
                                fireOnOneErrback=self._fire_on_first_eb,
                                consumeErrors=self._consume_errors)

        def chain_callback(r, d):
            d.callback(r)
            return d

        def chain_errback(r, d):
            d.errback(r)
            return d

        args = (fld, )
        dl.addCallbacks(chain_callback, chain_errback,
                        callbackArgs=args, errbackArgs=args)

        return dl
