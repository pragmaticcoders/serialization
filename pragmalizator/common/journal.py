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
import weakref

from twisted.internet import defer
from twisted.python import failure
from zope.interface import implements

from pragmalizator.common import decorator, fiber, error, registry
from pragmalizator.common import annotate, reflect, serialization
from pragmalizator.common.serialization.base import MetaSerializable
from pragmalizator.common.annotate import MetaAnnotable

from pragmalizator.interface.fiber import IFiber
from pragmalizator.interface.journal import JournalMode, IJournalReplayEntry
from pragmalizator.interface.journal import IRecorder, SideEffectResultError
from pragmalizator.interface.journal import IRecorderNode, IJournalKeeper
from pragmalizator.interface.journal import ReentrantCallError, RecordingResultError
from pragmalizator.interface.journal import IJournalEntry, ReplayError, IEffectHandler
from pragmalizator.interface.journal import IJournalSideEffect


RECORDING_TAG = "__RECORDING__"
RECMODE_TAG = "__RECMODE__"
JOURNAL_ENTRY_TAG = "__JOURNAL_ENTRY__"
SIDE_EFFECT_TAG = "__SIDE_EFFECT__"


def resolve_function(fun_id, function):
    global _registry, _reverse

    if function is None:
        # Retrieve the function from the registry
        function = _registry.lookup(fun_id)
        if function is None:
            raise AttributeError("No registered function found with "
                                 "identifier '%s'." % (fun_id, ))

    if fun_id is None:
        # Retrieve the identifier from the registry
        fun_id = _reverse.lookup(function)
        if fun_id is None:
            raise AttributeError("Function not register as recorded %r"
                                 % (function, ))

    return fun_id, function


def replay(journal_entry, function, *args, **kwargs):
    '''
    Calls method in replay context so that no journal entries are created,
    expected_side_effects are checked, and no asynchronous task is started.
    The journal entry is only used to fetch side-effects results.
    '''
    # Starts the fiber section
    section = fiber.WovenSection()
    section.enter()

    # Check if this is the first recording in the fiber section
    journal_mode = section.state.get(RECMODE_TAG, None)
    is_first = journal_mode is None

    if is_first:
        section.state[RECMODE_TAG] = JournalMode.replay
        section.state[JOURNAL_ENTRY_TAG] = IJournalReplayEntry(journal_entry)

    result = function(*args, **kwargs)

    # We don't want anything asynchronous to be called,
    # so we abort the fiber section
    section.abort(result)
    # side effects are returned in sake of making sure that
    # all the side effects expected have been consumed (called)
    return result


@decorator.parametrized_function
def recorded(function, custom_id=None, reentrant=True):
    '''MUST only be used only with method from child
    classes of L{{Recorder}}.'''
    canonical = reflect.class_canonical_name(3)
    annotate.injectClassCallback("recorded", 4,
                                 "_register_recorded_call",
                                 function, custom_id=custom_id,
                                 class_canonical_name=canonical)

    def wrapper(self, *args, **kwargs):
        recorder = IRecorder(self)
        return recorder.call(function, args, kwargs, reentrant=reentrant)

    return wrapper


@decorator.simple_callable
def side_effect(original):

    def wrapper(callable, *args, **kwargs):
        name = reflect.canonical_name(callable)
        return _side_effect_wrapper(callable, args, kwargs, name)

    return wrapper


@decorator.parametrized_callable
def named_side_effect(original, name):
    """Decorator for function or method that do not modify the recorder state
    but have some side effects that can't be replayed.
    What it does in recording mode is keep the function name, arguments,
    keyword and result as a side effect that will be recorded in the journal.
    In replay mode, it will only pop the next expected side-effect, verify
    the function name, arguments and keywords and return the expected result
    without executing the real function code. If the function name, arguments
    or keywords were to be different than the expected ones, it would raise
    L{ReplayError}. Should work for any function or method."""

    def wrapper(callable, *args, **kwargs):
        return _side_effect_wrapper(callable, args, kwargs, name)

    return wrapper


def _check_side_effet_result(result, info):
    if isinstance(result, defer.Deferred):
        raise SideEffectResultError("Side-effect functions %s "
                                    "cannot return Deferred" % info)
    if IFiber.providedBy(result):
        raise SideEffectResultError("Side-effect functions %s "
                                    "cannot return IFiber" % info)
    return result


def _side_effect_wrapper(callable, args, kwargs, name):
    section_state = fiber.get_state()

    if section_state is not None:
        # We are in a woven section

        entry = section_state.get(JOURNAL_ENTRY_TAG, None)

        if entry is not None:
            # We are in a replayable section
            mode = section_state.get(RECMODE_TAG, None)

            if mode == JournalMode.replay:
                return entry.next_side_effect(name, *args, **kwargs)

            # Create a side-effect entry
            effect = entry.new_side_effect(name, *args, **kwargs)
            # Keep it in the replayable section state
            section_state[SIDE_EFFECT_TAG] = effect
            # Break the fiber to allow new replayable sections
            fiber.break_fiber()
            # Keep the side-effect entry to detect we are in one
            fiber.set_stack_var(SIDE_EFFECT_TAG, effect)
            try:
                result = callable(*args, **kwargs)
                result = _check_side_effet_result(result, name)
                effect.set_result(result)
                effect.commit()
                return result
            except Exception, e:
                #FIXME: handle exceptions in side effects properly
                error.handle_exception(None, e,
                                       "Exception raised by side-effect %s",
                                       reflect.canonical_name(callable))
                raise

    # Not in a replayable section, maybe in another side-effect
    return _check_side_effet_result(callable(*args, **kwargs), name)


def add_effect(effect_id, *args, **kwargs):
    '''If inside a side-effect, adds an effect to it.'''
    effect = fiber.get_stack_var(SIDE_EFFECT_TAG)
    if effect is None:
        return False
    effect.add_effect(effect_id, *args, **kwargs)
    return True


class RecorderRoot(serialization.Serializable):

    implements(IRecorderNode)

    journal_parent = None

    def __init__(self, keeper, base_id=None):
        self.journal_keeper = IJournalKeeper(keeper)
        self._base_id = base_id and (base_id, ) or ()
        self._recorder_count = 0

    ### ISerializable Methods ###

    def recover(self, state):
        keeper, base, count = state
        self.journal_keeper = keeper
        self._base_id = base
        self._recorder_count = count

    def snapshot(self):
        return self.journal_keeper, self._base_id, self._recorder_count

    ### IRecorderNode Methods ###

    def generate_identifier(self, recorder):
        self._recorder_count += 1
        return self._base_id + (self._recorder_count, )


class RecorderNode(serialization.Serializable):

    implements(IRecorderNode)

    def __init__(self, parent):
        node = IRecorderNode(parent)
        identifier = node.generate_identifier(self)
        self.journal_parent = node
        self.journal_id = identifier
        self.journal_keeper = node.journal_keeper
        self._recorder_count = 0

    ### ISerializable Methods ###

    def recover(self, state):
        parent, keeper, ident, count = state
        self.journal_parent = parent
        self.journal_keeper = keeper
        self.journal_id = ident
        self._recorder_count = count

    def snapshot(self):
        return (self.journal_parent, self.journal_keeper,
                self.journal_id, self._recorder_count)

    ### IRecorderNode Methods ###

    def generate_identifier(self, recorder):
        self._recorder_count += 1
        return self.journal_id + (self._recorder_count, )


class Recorder(RecorderNode, annotate.Annotable):

    # Fix the metaclass inheritance
    # TODO: Changing order of superclasses below makes the MetaSerializer take
    # wrong type_name (the class name is substituted with '.recorded'.
    # This needs to be investigated, as it might show problem in MetaAnnotable
    __metaclass__ = type("MetaRecorder", (MetaSerializable, MetaAnnotable), {})

    implements(IRecorder)

    application = None

    @classmethod
    def _register_recorded_call(cls, function, custom_id=None,
                                class_canonical_name=None):
        global _registry, _reverse

        if custom_id is not None:
            fun_id = custom_id
        else:
            if class_canonical_name is None:
                class_canonical_name = ".".join([cls.__module__, cls.__name__])
            parts = [class_canonical_name, function.__name__]
            fun_id = ".".join(parts)

        # FIXME: Uncomment the code below after implementing proper cleanup
        # during module reloading
        # if fun_id in _registry and _registry[fun_id] != function:
        #     raise RuntimeError("Failed to register function %r with name
        #                        "'%s' it is already used by function %r"
        #                        % (function, fun_id, _registry[fun_id]))

        _registry.register(function, key=fun_id, application=cls.application)
        _reverse.register(fun_id, key=function, application=cls.application)

    def __init__(self, parent):
        RecorderNode.__init__(self, parent)
        self.journal_keeper.register(self)

    ### ISerializable ###

    def restored(self):
        self.journal_keeper.register(self)

    ### IRecorder Methods ###

    def record(self, fun_id, args=None, kwargs=None, reentrant=True):
        return self._recorded_call(fun_id, None, args or (), kwargs or {},
                                   reentrant=reentrant)

    def call(self, function, args=None, kwargs=None, reentrant=True):
        return self._recorded_call(None, function, args or (), kwargs or {},
                                   reentrant=reentrant)

    def replay(self, journal_entry):
        journal_entry = IJournalReplayEntry(journal_entry)
        fun_id = journal_entry.function_id
        args, kwargs = journal_entry.get_arguments()
        fun_id, function = self._resolve_function(fun_id, None)
        return replay(journal_entry, self._replayed_call,
                      fun_id, function, args, kwargs)

    ### Private Methods ###

    def _replayed_call(self, fun_id, function, args, kwargs):
        try:
            return self._call_fun(fun_id, function, args, kwargs)
        except Exception as e:
            return fiber.fail(e)

    def _recorded_call(self, fun_id, function, args, kwargs, reentrant=True):
        # Starts the fiber section
        section = fiber.WovenSection()
        section.enter()
        fibdesc = section.descriptor

        # Check if we are in replay mode
        mode = section.state.get(RECMODE_TAG, None)
        if mode == JournalMode.replay:
            fun_id, function = self._resolve_function(fun_id, function)
            return self._call_fun(fun_id, function, args, kwargs)

        # Check if this is the first recording in the fiber section
        recording = section.state.get(RECORDING_TAG, None)
        section_first = recording is None
        result = None

        try:

            entry = section.state.get(JOURNAL_ENTRY_TAG, None)
            mode = section.state.get(RECMODE_TAG, None)
            fiber_first = section_first and section.descriptor.fiber_depth == 0
            fun_id, function = self._resolve_function(fun_id, function)

            if section_first:
                entry = self.journal_keeper.new_entry(self.journal_id, fun_id,
                                                      *args, **kwargs)
                entry.set_fiber_context(fibdesc.fiber_id, fibdesc.fiber_depth)

                section.state[RECORDING_TAG] = True
                section.state[RECMODE_TAG] = JournalMode.recording
                section.state[JOURNAL_ENTRY_TAG] = entry

            if not (fiber_first or reentrant):
                # If not reentrant and it is not the first, it's BAAAAAD.
                raise ReentrantCallError("Recorded functions %s cannot be "
                                         "called from inside the recording "
                                         "section" % (fun_id, ))

            result = self._call_fun(fun_id, function, args, kwargs)

        except failure.Failure as f:
            # When trapping a failure it raised itself

            if not section_first:
                raise

            result = fiber.fail(f.value)
            error.handle_failure(self, f, "Failure inside recorded "
                                   "function %s", fun_id)

        except Exception as e:

            if not section_first:
                raise

            result = fiber.fail(e)
            error.handle_exception(self, e, "Exception inside recorded "
                                   "function %s", fun_id)

        finally:

            if section_first:
                entry.set_result(result)
                entry.commit()
                result = entry.get_result()
                section.state[RECORDING_TAG] = None
                section.state[JOURNAL_ENTRY_TAG] = None
                section.state[RECMODE_TAG] = None

        return section.exit(result)

    def _resolve_function(self, fun_id, function):
        return resolve_function(fun_id, function)

    def _call_fun(self, fun_id, function, args, kwargs):
        # Call the function
        result = function(self, *args, **kwargs)

        # Check the function result. Deferred are not allowed because
        # it would mean an asynchronous call chain is already started.
        if isinstance(result, defer.Deferred):
            raise RecordingResultError("Recorded functions %s "
                                       "cannot return Deferred" % fun_id)

        return result


class DummySideEffect(object):

    implements(IJournalSideEffect)

    ### IJournalSideEffect Methods ###

    def add_effect(self, effect_id, *args, **kwargs):
        return self

    def set_result(self, result):
        return self

    def commit(self):
        return self


class DummyJournalEntry(object):

    implements(IJournalEntry)

    def __init__(self):
        self._result = None
        self._dumy_side_effect = DummySideEffect()

    ### IJournalEntry Methods ###

    def set_fiber_context(self, fiber_id, fiber_depth):
        return self

    def new_side_effect(self, function_id, *args, **kwargs):
        return self._dumy_side_effect

    def set_result(self, result):
        self._result = result
        return self

    def commit(self):
        return self

    def get_result(self):
        return self._result


class DummyRecorderNode(object):

    implements(IRecorderNode, IJournalKeeper)

    def __init__(self):
        self.journal_keeper = self
        self._dummy_entry = DummyJournalEntry()

    ### IRecorderNode Methods ###

    def generate_identifier(self, _):
        return (None, )

    ### IJournalKeeper Methods ###

    def register(self, _):
        pass

    def new_entry(self, journal_id, function_id, *args, **kwargs):
        return self._dummy_entry


class StupidJournalSideEffect(object):

    implements(IJournalSideEffect)

    def __init__(self, keeper, record, function_id, *args, **kwargs):
        self._keeper = keeper
        self._record = record
        self._fun_id = function_id
        self._args = keeper.serializer.convert(args or None)
        self._kwargs = keeper.serializer.convert(kwargs or None)
        self._effects = []
        self._result = None

    ### IJournalSideEffect Methods ###

    def add_effect(self, effect_id, *args, **kwargs):
        assert self._record is not None
        data = (effect_id,
                self._keeper.serializer.convert(args),
                self._keeper.serializer.convert(kwargs))
        self._effects.append(data)

    def set_result(self, result):
        assert self._record is not None
        self._result = self._keeper.serializer.convert(result)
        return self

    def commit(self):
        assert self._record is not None
        data = (self._fun_id, self._args, self._kwargs,
                self._effects, self._result)
        self._record.extend(data)
        self._record = None
        return self


class StupidJournalEntry(object):
    '''Dummy in-memory journal entry, DO NOT USE for serious stuff.
    Values ARE NOT SERIALIZED so it cannot be used for replayability.'''

    implements(IJournalEntry, IJournalReplayEntry)

    @classmethod
    def from_record(cls, keeper, record):
        jid, fun_id, fid, fdepth, args, kwargs, effects, result = record
        entry = cls.__new__(cls)
        entry.journal_id = jid
        entry.function_id = fun_id

        entry._keeper = keeper
        entry._record = None
        entry.fiber_id = fid
        entry.fiber_depth = fdepth
        entry.frozen_result = result
        entry._args = args
        entry._kwargs = kwargs

        entry._side_effects = effects
        entry._next_effect = 0

        return entry

    def __init__(self, keeper, record, journal_id,
                 function_id, *args, **kwargs):
        self.journal_id = journal_id
        self.function_id = function_id

        self._keeper = keeper
        self._record = record
        self.fiber_id = None
        self.fiber_depth = None
        self.frozen_result = None
        self._args = keeper.serializer.convert(args or None)
        self._kwargs = keeper.serializer.convert(kwargs or None)

        self._side_effects = []
        self._next_effect = 0

    def add_side_effect(self, function_id, result, *args, **kwargs):
        effect = self.new_side_effect(function_id, *args, **kwargs)
        effect.set_result(result)
        effect.commit()
        return self

    ### IJournalReplayEntry Methods ###

    def get_arguments(self):
        return (self._keeper.unserializer.convert(self._args) or (),
                self._keeper.unserializer.convert(self._kwargs) or {})

    def rewind_side_effects(self):
        self._next_effect = 0

    def next_side_effect(self, function_id, *args, **kwargs):
        if self._next_effect >= len(self._side_effects):
            raise ReplayError("Unexpected side-effect function '%s'"
                              % function_id)

        expected = self._side_effects[self._next_effect]
        exp_fun_id, raw_args, raw_kwargs, effects, result = expected
        self._next_effect += 1

        if exp_fun_id != function_id:
            raise ReplayError("Unexpected side-effect function '%s' "
                              "instead of '%s'" % (function_id, exp_fun_id))

        exp_args = self._keeper.unserializer.convert(raw_args)
        if exp_args != (args or None):
            raise ReplayError("Unexpected side-effect arguments of function %r"
                              ", args: %r instead of %r" %\
                              (function_id, args or None, exp_args))

        exp_kwargs = self._keeper.unserializer.convert(raw_kwargs)
        if exp_kwargs != (kwargs or None):
            raise ReplayError("Unexpected side-effect keywords of function %r"
                              ", kwargs: %r instead of %r" %\
                              (function_id, kwargs or None, exp_kwargs))

        # Apply effects
        for effect_id, raw_args, raw_kwargs in effects:
            effect_args = self._keeper.unserializer.convert(raw_args)
            effect_kwargs = self._keeper.unserializer.convert(raw_kwargs)
            self._keeper.apply_effect(effect_id, *effect_args, **effect_kwargs)

        return self._keeper.unserializer.convert(result)

    ### IJournalEntry Methods ###

    def set_fiber_context(self, fiber_id, fiber_depth):
        assert self._record is not None
        self.fiber_id = fiber_id
        self.fiber_depth = fiber_depth
        return self

    def set_result(self, result):
        assert self._record is not None
        self.not_serialized_result = result
        self.frozen_result = self._keeper.serializer.freeze(result)
        return self

    def new_side_effect(self, function_id, *args, **kwargs):
        assert self._record is not None
        record = []
        self._side_effects.append(record)
        return StupidJournalSideEffect(self._keeper, record,
                                       function_id, *args, **kwargs)

    def commit(self):
        data = (self.journal_id, self.function_id,
                self.fiber_id, self.fiber_depth,
                self._args, self._kwargs,
                self._side_effects, self.frozen_result)
        self._record.extend(data)
        self._record = None
        return self

    def get_result(self):
        return self.not_serialized_result


class StupidJournalKeeper(RecorderRoot):
    '''Dummy in-memory journal keeper, DO NOT USE for serious stuff.
    Values ARE NOT SERIALIZED so it cannot be used for replayability.
    DO NOT RESPECT new_entry() ordering, entries are ordered by commit()
    call order.'''

    implements(IJournalKeeper, IEffectHandler)

    def __init__(self, serializer, unserializer, effect_handler=None):
        RecorderRoot.__init__(self, self)
        self.serializer = serializer
        self.unserializer = unserializer
        self._effect_handler = effect_handler
        self.clear()

    def get_records(self):
        return self._records

    def iter_entries(self):
        for record in self._records:
            yield StupidJournalEntry.from_record(self, record)

    def clear(self):
        self._records = []
        self._registry = weakref.WeakValueDictionary()

    def lookup(self, journal_id):
        return self._registry.get(journal_id)

    def iter_recorders(self):
        return self._registry.itervalues()

    ### IEffectHandler Methods ###

    def apply_effect(self, journal_id, *args, **kwargs):
        self._effect_handler.apply_effect(journal_id, *args, **kwargs)

    ### IJournalKeeper Methods ###

    def register(self, recorder):
        recorder = IRecorder(recorder)
        self._registry[recorder.journal_id] = recorder

    def new_entry(self, journal_id, function_id, *args, **kwargs):
        record = []
        self._records.append(record)
        return StupidJournalEntry(self, record, journal_id,
                                  function_id, *args, **kwargs)


class Registry(registry.BaseRegistry):

    allow_blank_application = True
    verify_interface = None


### Private Stuff ###

_registry = Registry() # {FUNCTION_ID: FUNCTION}
_reverse = Registry()  # {FUNCTION: FUNCTION_ID}
