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

from __future__ import absolute_import

import enum

from zope.interface.declarations import implementer
from zope.interface.interface import InterfaceClass

from past.types import unicode, long

from serialization import reflect
from serialization.interface import *

from serialization import base


@implementer(IExternal)
class External(object):
    '''Used by TreeSerializer to encapsulate external references.'''

    __slots__ = ("identifier", )

    @classmethod
    def _build(cls, data):
        identifier, = data
        return cls(identifier)

    def __init__(self, identifier):
        self.identifier = identifier

    def __repr__(self):
        return "<External %s>" % (self.identifier, )

    def __eq__(self, other):
        if not isinstance(other, External):
            return NotImplemented
        return self.identifier == other.identifier

    def __ne__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return not self.__eq__(other)


@implementer(IInstance)
class Instance(object):
    '''Used by TreeSerializer to encapsulate ISerializable instances.
    Implements L{IInstance} and can be compared for equality.'''

    __slots__ = ("type_name", "snapshot")

    @classmethod
    def _build(cls, data):
        type_name, snapshot = data
        return cls(type_name, snapshot)

    def __init__(self, type_name, snapshot):
        self.type_name = type_name
        self.snapshot = snapshot

    def __repr__(self):
        return "<Instance %s: %r>" % (self.type_name, self.snapshot)

    def __eq__(self, other):
        if not isinstance(other, Instance):
            return NotImplemented
        return (self.type_name == other.type_name
                and self.snapshot == other.snapshot)

    def __ne__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return not self.__eq__(other)


@implementer(IReference)
class Reference(object):
    '''Used by TreeSerializer to encapsulate references.
    Can be compared for equality and hashed if the referenced
    value is hashable. Implements L{IReference}.'''

    __slots__ = ("refid", "value")

    @classmethod
    def _build(cls, data):
        refid, value = data
        return cls(refid, value)

    def __init__(self, refid, value):
        self.refid = refid
        self.value = value

    def __repr__(self):
        return "<Reference %s: %r>" % (self.refid, self.value)

    def __hash__(self):
        # Make references hashable to be able to use them as dict key
        return hash(self.refid) ^ hash(self.value)

    def __eq__(self, other):
        if not isinstance(other, Reference):
            return NotImplemented
        return (self.refid == other.refid
                and self.value == other.value)

    def __ne__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return not self.__eq__(other)


@implementer(IDereference)
class Dereference(object):
    '''Used by TreeSerializer to encapsulate a dereference to a previous
    referenced value. Can be compared for equality and hashed.
    Implements L{IDereference}.'''

    __slots__ = ("refid", )

    def __init__(self, refid):
        self.refid = refid

    def __repr__(self):
        return "<Dereference %s>" % self.refid

    def __hash__(self):
        # Make dereferences hashable to be able to use them as dict key
        return hash(self.refid)

    def __eq__(self, other):
        if not isinstance(other, Dereference):
            return NotImplemented
        return self.refid == other.refid

    def __ne__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return not self.__eq__(other)


class Serializer(base.Serializer):
    '''Serialize any python structure to a tree of basic python types,
    L{IInstance}, L{IReference} and L{IDereference}.

    Object have to implement L{ISerializable} to be serialized.

    Examples::

        >> a = [1, 2, 3]
        >> b = [4, 5, 6]
        >> c = ['X', a, 'Y', b, 'Z', a]
        >> print(TreeSerializer().convert(c))
        ['X', <Reference 1: [1, 2, 3]>, 'Y', [4, 5, 6], 'Z', <Derefence: 1>]

        >> o = Serializable()
        >> o.foo = 42
        >> print(TreeSerializer().convert(o))
        <Instance serialization.Serializable: {"foo": 42}>

    '''

    pack_tuple = tuple
    pack_set = set
    pack_dict = dict
    pack_instance = Instance._build
    pack_reference = Reference._build
    pack_dereference = Dereference
    pack_external = External._build

    def __init__(self, post_converter=None, externalizer=None,
                 source_ver=None, target_ver=None):
        base.Serializer.__init__(self, post_converter=post_converter,
                                 externalizer=externalizer,
                                 source_ver=source_ver,
                                 target_ver=target_ver)

    def pack_frozen_external(self, value):
        identifier, = value
        return identifier

    def pack_frozen_instance(self, value):
        content, = value
        return content

    def pack_frozen_function(self, value):
        return reflect.canonical_name(value)

    pack_frozen_method = pack_frozen_function
    pack_frozen_builtin = pack_frozen_function


class Unserializer(base.Unserializer):
    '''Unserialize a structure serialized with L{pytree.Serializer}.
    The complexity in unserializing from python object tree is that
    set and dictionary are not ordered. Because of that we cannot
    ensure references are processed before being dereferenced.
    The base class raises DelayUnpacking exception when an unknown
    reference got dereferenced, so unpacking '''

    pass_through_types = set([str, unicode, int, long, float, bool,
                              type(None), type, InterfaceClass, enum.Enum])

    def __init__(self, pre_converter=None, registry=None, externalizer=None,
                 source_ver=None, target_ver=None):
        base.Unserializer.__init__(self, pre_converter=pre_converter,
                                   registry=registry,
                                   externalizer=externalizer,
                                   source_ver=source_ver,
                                   target_ver=target_ver)

    ### Overridden Methods ###

    def analyse_data(self, data):
        data_type = type(data)

        lookup = self._unpackers.get(data_type)
        if lookup is not None:
            return lookup

        # Handle references, dereferences and instances
        # We want to be compatible with all implementations
        # of the interface so we cannot use lookup table

        if IInstance.providedBy(data):
            return data.type_name, Unserializer.unpack_instance

        if IDereference.providedBy(data):
            return None, Unserializer.unpack_dereference

        if IReference.providedBy(data):
            return None, Unserializer.unpack_reference

        if IExternal.providedBy(data):
            return None, Unserializer.unpack_external

    ### Private Methods ###

    def unpack_instance(self, data, *args):
        return self.restore_instance(data.type_name, data.snapshot, *args)

    def unpack_external(self, data):
        return self.restore_external(data.identifier)

    def unpack_reference(self, data):
        return self.restore_reference(data.refid, data.value)

    def unpack_dereference(self, data):
        return self.restore_dereference(data.refid)

    def unpack_tuple(self, data):
        return tuple([self.unpack_data(d) for d in data])

    def unpack_list(self, container, data):
        container.extend([self.unpack_data(d) for d in data])

    def unpack_set(self, container, data):
        container.update(self.unpack_unordered_values(data))

    def unpack_dict(self, container, data):
        container.update(self.unpack_unordered_pairs(data.items()))

    _unpackers = {tuple: (None, unpack_tuple),
                  list: (list, unpack_list),
                  set: (set, unpack_set),
                  dict: (dict, unpack_dict)}
