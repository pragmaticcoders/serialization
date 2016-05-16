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

from six import with_metaclass, iterkeys, iteritems
import copy

import serialization
from . import annotate


class Field(object):

    def __init__(self, name, default, serialize_as=None, **meta):
        self.name = name
        self.default = default
        self.serialize_as = serialize_as or name
        self._meta = meta

    def __repr__(self):
        return "%r default %r" % (self.name, self.default, )

    def meta(self, name):
        return self._meta.get(name)


def field(name, default, serialize_as=None, **meta):
    f = Field(name, default, serialize_as, **meta)
    annotate.injectClassCallback("field", 3, "_register_field", f)


class MetaFormatable(type(serialization.Serializable),
                     type(annotate.Annotable)):
    pass


class Formatable(with_metaclass(
        MetaFormatable,
        serialization.Serializable, annotate.Annotable)):

    @classmethod
    def __class__init__(cls, name, bases, dct):
        cls._fields = list()

        for base in bases:
            if not issubclass(type(base), MetaFormatable):
                continue
            cls._fields += copy.deepcopy(base._fields)

    @classmethod
    def _register_field(cls, field):
        # remove field with this name if already present (overriding defaults)
        [cls._fields.remove(x) for x in cls._fields if x.name == field.name]
        cls._fields.append(field)

    def __init__(self, **fields):
        self._set_fields(fields)

    def __repr__(self):
        return "<%s %r>" % (type(self).__name__, self.snapshot(), )

    def _set_fields(self, dictionary):
        properties = dict()
        for key in list(iterkeys(dictionary)):
            find = [x for x in self._fields if x.name == key]
            if len(find) != 1:
                p = getattr(type(self), key, None)
                if isinstance(p, property):
                    # store property setters for later
                    properties[key] = dictionary.pop(key)
                else:
                    raise AttributeError(
                        "Class %r doesn't have the %r attribute." %\
                        (type(self), key, ))

        for field in self._fields:
            # lazy coping of default value, don't touch!
            if field.name in dictionary:
                value = dictionary[field.name]
            else:
                value = copy.copy(field.default)
            setattr(self, field.name, value)

        # finally process the property setters
        for key, value in iteritems(properties):
            setattr(self, key, value)

    def __eq__(self, other):
        if type(self) != type(other):
            return NotImplemented
        for field in self._fields:
            if getattr(self, field.name) != getattr(other, field.name):
                return False
        return True

    def __ne__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return not self.__eq__(other)

    # ISerializable

    def snapshot(self):
        res = dict()
        for field in self._fields:
            value = getattr(self, field.name)
            if field.default is not None or value is not None:
                res[field.serialize_as] = value
        return res

    def recover(self, snapshot):
        for field in self._fields:
            # lazy coping of default value, don't touch!
            if field.serialize_as in snapshot:
                value = snapshot[field.serialize_as]
            else:
                value = copy.copy(field.default)
            setattr(self, field.name, value)


class MetaVersionedFormatable(
        type(Formatable), type(serialization.VersionAdapter)):
    pass


class VersionedFormatable(
        with_metaclass(
            MetaVersionedFormatable, Formatable, serialization.VersionAdapter)):

    version = 1

    def store_version(self, snapshot, version, version_atom):
        snapshot[version_atom] = version
        return snapshot
