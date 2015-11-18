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

from __future__ import absolute_import

import types
from six import with_metaclass
from past.types import unicode

from serialization.common.decorator import unicode_args


class MetaEnum(type):

    def __init__(cls, name, bases, namespace):
        type.__init__(cls, name, bases, namespace)
        if bases == (int, ): # Base Enum class
            return

        cls._names = {}  # {str: Enum}
        cls._values = {} # {int: Enum}
        cls._items = {}  # {Enum: str}
        for key, value in namespace.items():
            if not isinstance(value, types.FunctionType):
                if not key.startswith("_"):
                    cls.add(key, value)

    def add(cls, attr, value=None):
        if value is None:
            value = max(cls._values.keys()) + 1
        if isinstance(value, tuple) and len(value) == 2:
            value, name = value
        else:
            name = attr

        if not isinstance(value, int):
            raise TypeError("Enum value type must be int not %s"
                             % (value.__class__.__name__))
        if value in cls._values:
            raise ValueError(
                "Error while creating enum %s of type %s, "
                "it has already been created as %s" % (
                value, cls.__name__, cls._values[value]))

        self = super(Enum, cls).__new__(cls, value)
        self.name = name

        cls._values[value] = self
        cls._names[name] = self
        cls._items[self] = name
        setattr(cls, attr, self)

        return self

    @unicode_args
    def get(cls, key):
        """
        str, int or Enum => Enum
        """
        if isinstance(key, Enum) and not isinstance(key, cls):
            raise TypeError("Cannot type cast between enums")
        if isinstance(key, int):
            if not int(key) in cls._values:
                raise KeyError("There is no enum with key %d" % key)
            return cls._values[key]
        if isinstance(key, (bytes, unicode)):
            if not key in cls._names:
                raise KeyError("There is no enum with name %s" % key)
            return cls._names[key]
        raise TypeError("Invalid enum key type: %s"
                         % (key.__class__.__name__))

    __getitem__ = get

    def __contains__(cls, key):
        if isinstance(key, (str, unicode)):
            return key in cls._names
        if isinstance(key, Enum) and not isinstance(key, cls):
            raise TypeError("Cannot type cast between enums")
        return int(key) in cls._values

    def __len__(cls):
        return len(cls._values)

    def __iter__(cls):
        return iter(cls._items)

    def items(cls):
        return cls._items.items()

    def iteritems(cls):
        return cls._items.items()

    def values(cls):
        return cls._items.values()

    def itervalues(cls):
        return cls._items.itervalues()

    def keys(cls):
        return cls._items.keys()

    def iterkeys(cls):
        return cls._items.iterkeys()


class Enum(with_metaclass(MetaEnum, int)):
    """
    enum is an enumered type implementation in python.

    To use it, define an enum subclass like this:

    >>> from serialization.common.enum import Enum
    >>>
    >>> class Status(Enum):
    >>>     OPEN, CLOSE = range(2)
    >>> Status.OPEN
    '<Status value OPEN>'

    All the integers defined in the class are assumed to be enums and
    values cannot be duplicated
    """

    def __new__(cls, value):
        return cls.get(value)

    def __cmp__(self, value):
        if value is None:
            return NotImplemented
        if isinstance(value, Enum) and not isinstance(value, type(self)):
            raise TypeError("Cannot compare between enums")
        try:
            return super(Enum, self).__cmp__(value)
        except TypeError:
            # this happens when we try to compare to something
            # which is not enum
            return NotImplemented

    def __str__(self):
        return '<%s value %s>' % (
            self.__class__.__name__, self.name)

    def __nonzero__(self):
        return True

    __repr__ = __str__


def value(number, name=None):
    if name is None:
        return number
    return number, name
