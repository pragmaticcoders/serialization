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

import heapq
import sys

from zope.interface import implements, classProvides

from pragmalizator.common import serialization, defer
from pragmalizator.interface.generic import ITimeProvider


__all__ = ("MroDict", "MroList", "MroDictOfList",
           "Empty", "ExpDict", "ExpQueue")

PRECISION = 1e3
MAX_LAZY_PACK_PER_SECOND = 1


class Empty(Exception):
    pass


class MroDataDescriptor(object):
    """
    Base MRO aware descriptor used to create
    inheritance friendly class level data structure.
    @cvar proxy_factory: factory to create data structure proxies.
    """

    proxy_factory = None

    def __init__(self, tag):
        """
        @param tag: attribute name used to store private
                    data inside each classes.
        @type tag: str
        """
        self._tag = tag

    ### descriptor protocol ###

    def __get__(self, obj, owner):
        klasses = owner.mro()
        klasses.reverse()

        values = self._create_values()
        for klass in klasses:
            if self._has_blackbox(klass):
                blackbox = self._get_blackbox(klass)
                result = self._consolidate_values(values, blackbox)
                values = result if result is not None else values

        return self.proxy_factory(self._ensure_blackbox(owner), values)

    ### endof descriptor protocol ###

    def _has_blackbox(self, cls):
        return self._tag in cls.__dict__

    def _get_blackbox(self, cls):
        if self._tag in cls.__dict__:
            return getattr(cls, self._tag)
        return None

    def _ensure_blackbox(self, cls):
        if self._tag not in cls.__dict__:
            blackbox = self._create_blackbox()
            setattr(cls, self._tag, blackbox)
        else:
            blackbox = getattr(cls, self._tag)
        return blackbox

    ### virtual ###

    def _create_blackbox(self):
        """
        Overrides to create the private data structure
        each classes hold to store there part of the data.
        @return: a black box stored in a class, each classes having there own.
        @rtype: Any
        """

    def _create_values(self):
        """
        Overrides to create the public data structure
        where all data is consolidated. This is not the proxy
        but the data passed to the proxy as the consolidated data.
        @return: a value used to consolidate the private black boxes
                 and passed to the proxy.
        @rtype: Any
        """

    def _consolidate_values(self, values, private):
        """
        Overrides to consolidate a public value with private data.
        @return: the consolidated values.
        @rtype: Any
        """


class MroProxy(object):
    """Provides a generic proxy delegating to the values."""

    delegated = []

    def __init__(self, blackbox, values):
        self._blackbox = blackbox
        self._values = values

    def __getattr__(self, attr):
        if attr in self.delegated:
            value = getattr(self._values, attr)
            setattr(self, attr, value)
            return value
        raise AttributeError(attr)


class MroDictProxy(MroProxy):
    """
    I provide a dict-like protocol for MRO class dictionaries.
    I provide some immutable methods and item setting.
    """

    delegated = ["keys", "values", "items",
                 "iterkeys", "itervalues", "iteritems", "get"]

    ### dict protocol ###

    def __len__(self):
        return len(self._values)

    def __contains__(self, value):
        return value in self._values

    def __getitem__(self, name):
        return self._values[name]

    def __iter__(self):
        return iter(self._values)

    def __setitem__(self, key, value):
        self._blackbox[key] = value
        self._values[key] = value


class MroDict(MroDataDescriptor):
    """
    I'm an dictionary which is meant to be used as a class attribute.
    I'm aware of MRO and show different values depending from which class
    i'm accessed.

    NOTE: Keep in mind that accessible mro dictionary in results in two
    dictionaries being instantiated. The is expensive operation, in case of
    performing multiple operations in single method it is recommended to
    assign it to local variable.
    """

    proxy_factory = MroDictProxy

    ### overridden ###

    def _create_blackbox(self):
        return {}

    def _create_values(self):
        return {}

    def _consolidate_values(self, values, private):
        values.update(private)


class MroListProxy(MroProxy):
    """
    I provide a list-like protocol to access the MRO list.
    I provide some immutable methods, append and extend.
    """

    delegated = []

    ### list protocol ###

    def __len__(self):
        return len(self._values)

    def __contains__(self, value):
        return value in self._values

    def __getitem__(self, index):
        return self._values[index]

    def __iter__(self):
        return iter(self._values)

    def append(self, value):
        self._values.append(value)
        self._blackbox.append(value)

    def extend(self, values):
        self._values.extend(values)
        self._blackbox.extend(values)


class MroList(MroDataDescriptor):
    """
    I'm a list descriptor providing a list inheriting parent class values
    with the ability for each classes to add there own values without
    polluting any of the other base class children.
    The order of the values is determined by the class MRO order.
    """

    proxy_factory = MroListProxy

    ### overridden ###

    def _create_blackbox(self):
        return []

    def _create_values(self):
        return []

    def _consolidate_values(self, values, private):
        values.extend(private)


class MroDictOfListProxy(MroProxy):
    """
    I provide a dict-like protocol to access the MRO dict of list.
    I provide some immutable methods and methods to append values
    to a name identifier item.
    """

    delegated = ["keys", "iterkeys"]

    ### dict protocol ###

    def __len__(self):
        return len(self._values)

    def __contains__(self, value):
        return value in self._values

    def __getitem__(self, name):
        return list(self._values[name])

    def __iter__(self):
        return iter(self._values)

    def values(self):
        return list(self.itervalues())

    def itervalues(self):
        return (list(v) for v in self._values.itervalues())

    def items(self):
        return list(self.iteritems())

    def iteritems(self):
        return ((k, list(v)) for k, v in self._values.iteritems())

    def get(self, name, default=None):
        if name in self._values:
            return list(self._values.get(name))
        return default

    ### public ###

    def put(self, name, value):
        v = self._values.setdefault(name, [])
        v.append(value)
        r = self._blackbox.setdefault(name, [])
        r.append(value)

    def aggregate(self, name, values):
        v = self._values.setdefault(name, [])
        v.extend(values)
        r = self._blackbox.setdefault(name, [])
        r.extend(values)


class MroDictOfList(MroDataDescriptor):
    """
    I'm a descriptor providing a collection of values identified by name
    built from the chain of class inheritance with the ability for each
    classes to add there own values without polluting any of the other
    base class children.
    The order of the values is determined by the class MRO order.
    """

    proxy_factory = MroDictOfListProxy

    ## overridden ###

    def _create_blackbox(self):
        return {}

    def _create_values(self):
        return {}

    def _consolidate_values(self, values, private):
        for k, v in private.iteritems():
            l = values.setdefault(k, [])
            l.extend(v)


class ExpBase(object):

    ### ISerializable Method ###

    def snapshot(self):
        """Should return a python structure."""

    def recover(self, snapshot):
        """Should recover from a snapshot."""

    def restored(self):
        """Called when everything has been recovered."""

    ### IRestorator Method ###

    @classmethod
    def prepare(cls):
        return cls.__new__(cls)


class RunningAverage(object):

    def __init__(self, default):
        self._default = default
        self._nominator = 0
        self._denominator = 0

    def get_value(self):
        try:
            return float(self._nominator) / self._denominator
        except ZeroDivisionError:
            return self._default

    def add_point(self, value):
        self._nominator += value
        self._denominator += 1


@serialization.register
class ExpDict(ExpBase):
    """
    @warning: Getting the length, and therefore construct like
              "if exp_dict: ..." or "bool(exp_dict)",
              will iterate over all elements.
    @warning: Comparison operations are very expensive.
    """

    DEFAULT_MAX_SIZE = 100

    type_name = "xdict"

    classProvides(serialization.IRestorator)
    implements(serialization.ISerializable)

    __slots__ = ("_time", "_items", "_max_size", "_last_pack")

    def __init__(self, time_provider, max_size=None):
        """Create an expiration dictionary.
        @param time_provider: who provide the time
        @type time_provider: L{ITimeProvider}
        @param max_size: maximum size before forced packing
        @type max_size: int"""
        self._time = ITimeProvider(time_provider)
        self._items = {} # {KEY: ExpItem(TIME, VALUE)}
        self._max_size = RunningAverage(max_size or self.DEFAULT_MAX_SIZE)
        self._last_pack = 0

    def clear(self):
        """Removes all items from the dictionary."""
        self._items.clear()

    def pack(self):
        """Packs the dictionary by removing all expired items."""
        self._pack(self._time.get_time())

    def set(self, key, value=None, expiration=None, relative=False):
        """Adds an entry to the dictionary with specified expiration and value.
        @param key: unique key of the entry, used to remove or test ownership
        @type key: any immutable
        @param value: black box associated with the key
        @type value: any python structure or L{ISerializable}
        @param expiration: the time at which the entry will expire.
        @type expiration: float
        @param relative: if the specified expiration time is relative
                         to EPOC UTC or from now.
        @type relative: bool
        @return: nothing"""
        self._lazy_pack()
        if expiration is not None:
            now = self._time.get_time()
            if relative:
                expiration = now + expiration
            if expiration <= now:
                return
        self._items[key] = ExpItem(expiration, value)

    def remove(self, key):
        """Removes the dictionary entry with with specified key .
        @param key: unique key of the entry, used to remove or test ownership
        @type key: any immutable
        @return: item value
        @rtype: any python structure or L{ISerializable}"""
        self._lazy_pack()
        now = self._time.get_time()
        if self._items:
            item = self._items.pop(key)
            if item.exp is None or item.exp > now:
                return item.value
        raise KeyError(key)

    def pop(self, key, *default):
        """Pops and returns the dictionary entry with with specified key.
        @param key: unique key of the entry, used to remove or test ownership
        @type key: any immutable
        @return: value
        @rtype: any python structure or L{ISerializable}"""
        self._lazy_pack()
        now = self._time.get_time()
        if self._items:
            try:
                item = self._items.pop(key)
                if item.exp is None or item.exp > now:
                    return item.value
                raise KeyError(key)
            except KeyError:
                if len(default) == 1:
                    return default[0]
                else:
                    raise

    def get(self, key, default=None):
        """Retrieve value from the entry with specified key.
        @param key: unique key of the entry, used to remove or test ownership
        @type key: any immutable
        @param default: value returned if no entry is found with specified key
        @type default: any python structure or L{ISerializable}
        @return: entry value or default value
        @rtype: any python structure or L{ISerializable}"""
        item = self._get_item(key)
        return default if item is None else item.value

    def get_expiration(self, key):
        item = self._get_item(key)
        if item is None:
            raise KeyError(key)
        return item.exp

    def iterkeys(self):
        """Returns an iterator over the dictionary keys."""
        self._lazy_pack()
        now = self._time.get_time()
        for key, item in self._items.iteritems():
            if item.exp is None or item.exp > now:
                yield key
                now = self._time.get_time()

    def itervalues(self):
        """Returns an iterator over the dictionary values."""
        self._lazy_pack()
        now = self._time.get_time()
        for item in self._items.itervalues():
            if item.exp is None or item.exp > now:
                yield item.value
                now = self._time.get_time()

    def values(self):
        return list(self.itervalues())

    def keys(self):
        return list(self.iterkeys())

    def iteritems(self):
        """Returns an iterator over tuples (key, value)."""
        self._lazy_pack()
        now = self._time.get_time()
        for key, item in self._items.iteritems():
            if item.exp is None or item.exp > now:
                yield key, item.value
                now = self._time.get_time()

    def size(self):
        """Returns the current size counting expired elements."""
        return len(self._items)

    def __setitem__(self, key, value):
        self._lazy_pack()
        self._items[key] = ExpItem(None, value)

    def __getitem__(self, key):
        item = self._get_item(key)
        if item is not None:
            return item.value
        raise KeyError(key)

    def __delitem__(self, key):
        item = self._get_item(key)
        if item is not None:
            del self._items[key]
            return
        raise KeyError(key)

    def __contains__(self, key):
        return self._get_item(key) is not None

    def __iter__(self):
        return self.iterkeys()

    def __len__(self):
        now = self._time.get_time()
        return len([i for i in self._items.itervalues()
                    if i.exp is None or i.exp > now])

    def __eq__(self, other):
        if not issubclass(type(other), type(self)):
            return NotImplemented
        now = self._time.get_time()
        a = [(k, i.pri, i.value)
             for k, i in self._items.iteritems()
             if i.exp is None or i.exp > now]
        b = [(k, i.pri, i.value)
             for k, i in other._items.iteritems()
             if i.exp is None or i.exp > now]
        a.sort()
        b.sort()
        return a == b

    def __ne__(self, other):
        eq = self.__eq__(other)
        return eq if eq == NotImplemented else not eq

    def __repr__(self):
        values = ["%s=%s" % (k, v) for k, v in self.iteritems()]
        return "<xdict: {%s}>" % (", ".join(values), )

    ### ISerializable Method ###

    def snapshot(self):
        return (self._time, self._max_size.get_value(),
                dict([(k, i.snapshot()) for k, i in self._items.iteritems()]))

    def recover(self, snapshot):
        self._time, max_size, data = snapshot
        self._max_size = RunningAverage(max_size)
        self._items = dict([(k, ExpItem.restore(s))
                            for k, s in data.iteritems()])
        self._last_pack = 0

    ### Private Methods ###

    def _lazy_pack(self):
        if len(self._items) > self._max_size.get_value() * 1.25:
            now = self._time.get_time()
            # Regulate lazy packing rate
            if (now - self._last_pack) >= (1.0 / MAX_LAZY_PACK_PER_SECOND):
                self._pack(now)

    def _pack(self, now):
        self._items = dict([(k, i) for k, i in self._items.iteritems()
                            if i.exp is None or i.exp > now])
        self._last_pack = now
        self._max_size.add_point(len(self._items))

    def _get_item(self, key):
        self._lazy_pack()
        now = self._time.get_time()
        item = self._items.get(key, None)
        if item is not None:
            if item.exp is None or item.exp > now:
                return item
            del self._items[key]
        return None


@serialization.register
class ExpQueue(ExpBase):
    """
    @warning: Getting the length, and therefore constructs like
              "if exp_dict: ..." or "bool(exp_dict)"
              will iterate over all elements.
    @warning: Comparison operations are very expensive.
    """

    DEFAULT_MAX_SIZE = 100

    type_name = "xqueue"

    classProvides(serialization.IRestorator)
    implements(serialization.ISerializable)

    __slots__ = ("_time", "_heap", "_max_size", "_last_pack")

    def __init__(self, time_provider, max_size=None, on_expire=None):
        """Create an expiration queue.
        @param time_provider: who provide the time
        @type time_provider: L{ITimeProvider}
        @param max_size: maximum size before forced packing
        @type max_size: int"""
        self._time = ITimeProvider(time_provider)
        self._heap = []
        self._max_size = RunningAverage(max_size or self.DEFAULT_MAX_SIZE)
        self._last_pack = 0
        self._on_expire = on_expire

    def pack(self):
        """Packs the set by removing all expired items."""
        self._pack(self._time.get_time())

    def clear(self):
        """Removes all the values from the queue."""
        self._heap = []

    def add(self, value, expiration=None, relative=False):
        """Adds an entry to the queue with specified expiration and value.
        @param value: black box associated with the key
        @type value: any python structure or L{ISerializable}
        @param expiration: the time at which the entry will expire.
        @type expiration: float
        @param relative: if the specified expiration time is relative
                         to EPOC UTC or from now.
        @type relative: bool
        @return: nothing"""
        self._lazy_pack()
        now = self._time.get_time()
        if expiration is not None:
            now = self._time.get_time()
            if relative:
                expiration = now + expiration
            if expiration <= now:
                return
        heapq.heappush(self._heap, ExpItem(expiration, value))

    def pop(self):
        """Pops and returns the value with the smaller expiration.
        @returns: value
        @rtype: any python structure or L{ISerializable}"""
        self._lazy_pack()
        now = self._time.get_time()
        while True:
            try:
                item = heapq.heappop(self._heap)
                if item.exp is None or item.exp > now:
                    return item.value
                elif callable(self._on_expire):
                    self._on_expire(item.value)
            except IndexError:
                raise Empty(), None, sys.exc_info()[2]

    def size(self):
        """Returns the current size counting expired values."""
        return len(self._heap)

    def __iter__(self):
        """Returns an iterator over queue's values."""
        self._lazy_pack()
        now = self._time.get_time()
        for item in iter(self._heap):
            if item.exp is None or item.exp > now:
                yield item.value
                now = self._time.get_time()

    def __len__(self):
        now = self._time.get_time()
        return len([i for i in self._heap
                    if i.exp is None or i.exp > now])

    def __eq__(self, other):
        if not issubclass(type(other), type(self)):
            return NotImplemented
        now = self._time.get_time()
        a = [(i.pri, i.value)
             for i in self._heap
             if i.exp is None or i.exp > now]
        b = [(i.pri, i.value)
             for i in other._heap
             if i.exp is None or i.exp > now]
        a.sort()
        b.sort()
        return a == b

    def __ne__(self, other):
        eq = self.__eq__(other)
        return eq if eq == NotImplemented else not eq

    ### ISerializable Method ###

    def snapshot(self):
        now = self._time.get_time()
        return self._time, [i.snapshot()
                            for i in self._heap
                            if i.exp is None or i.exp > now]

    def recover(self, snapshot):
        self._time, data = snapshot
        self._heap = [ExpItem.restore(d) for d in data]
        self._last_pack = 0

    ### Private Methods ###

    def _lazy_pack(self):
        if len(self._heap) > self._max_size.get_value() * 1.25:
            now = self._time.get_time()
            # Regulate lazy packing rate
            if (now - self._last_pack) >= (1.0 / MAX_LAZY_PACK_PER_SECOND):
                self._pack(now)

    def _pack(self, now):
        new_heap = []
        for i in self._heap:
            if i.exp is None or i.exp > now:
                new_heap.append(i)
            elif callable(self._on_expire):
                self._on_expire(i.value)

        heapq.heapify(new_heap)
        self._heap = new_heap
        self._last_pack = now
        self._max_size.add_point(len(new_heap))


class AsyncDict(object):

    def __init__(self):
        self._values = []
        self._info = []

    def add_if_true(self, key, value):
        self.add(key, value, bool)

    def add_if_not_none(self, key, value):
        self.add(key, value, lambda v: v is not None)

    def add_result(self, key, value, method_name, *args, **kwargs):
        if not isinstance(value, defer.Deferred):
            value = defer.succeed(value)
        value.addCallback(self._call_value, method_name, *args, **kwargs)
        self.add(key, value)

    def add(self, key, value, condition=None):
        if not isinstance(value, defer.Deferred):
            value = defer.succeed(value)
        self._info.append((key, condition))
        self._values.append(value)

    def wait(self):
        d = defer.DeferredList(self._values, consumeErrors=True)
        d.addCallback(self._process_values)
        return d

    ### private ###

    def _process_values(self, param):
        return dict((k, v) for (s, v), (k, c) in zip(param, self._info)
                    if s and (c is None or c(v)))

    def _call_value(self, value, method_name, *args, **kwargs):
        return getattr(value, method_name)(*args, **kwargs)


## Private Stuff ###


class ExpItem(object):
    """
    Encapsulate an item with expiration.
    It compares with other ExpItem using expiration time
    up to a resolution of a millisecond.
    In other words, if ExpItem have an expiration difference
    of less than a millisecond they will be evaluated equal.
    """

    __slots__ = ("exp", "value")

    @classmethod
    def restore(cls, snapshot):
        pri, value = snapshot
        exp = None if pri is None else float(pri) / PRECISION
        return cls(exp, value)

    def __init__(self, exp, value):
        self.exp = exp
        self.value = value

    @property
    def pri(self):
        if self.exp is None:
            return None
        return int(round(self.exp * PRECISION))

    def __cmp__(self, other):
        # None has always the least priority
        if self.exp is None:
            if other.exp is None:
                return 0
            return 1
        elif other.exp is None:
            return -1

        diff = (self.exp * PRECISION) - (other.exp * PRECISION)
        return int(round(diff))

    def snapshot(self):
        return self.pri, self.value

### Private Stuff ###
