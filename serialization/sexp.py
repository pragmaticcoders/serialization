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

from past.types import long
from builtins import bytes

from serialization import reflect

from serialization import base

UNICODE_ATOM = "unicode"
UNICODE_FORMAT_ATOM = "UTF-8"

BOOL_ATOM = "boolean"
BOOL_TRUE_ATOM = "true"
BOOL_FALSE_ATOM = "false"
NONE_ATOM = "None"

TUPLE_ATOM = "tuple"
LIST_ATOM = "list"
SET_ATOM = "set"
DICT_ATOM = "dictionary"

CLASS_ATOM = "class"
ENUM_ATOM = "enum"
EXTERNAL_ATOM = "external"

REFERENCE_ATOM = "reference"
DEREFERENCE_ATOM = "dereference"


class Serializer(base.Serializer):
    '''Serialize any python structure into s-expression compatible
    with twisted.spread.jelly.'''

    def __init__(self, post_converter=None, externalizer=None,
                 converter_caps=None, freezer_caps=None,
                 source_ver=None, target_ver=None):
        base.Serializer.__init__(self, post_converter=post_converter,
                                 externalizer=externalizer,
                                 converter_caps=converter_caps,
                                 freezer_caps=freezer_caps,
                                 source_ver=source_ver,
                                 target_ver=target_ver)

    def pack_unicode(self, value):
        return [UNICODE_ATOM, value.encode(UNICODE_FORMAT_ATOM)]

    def pack_bool(self, value):
        return [BOOL_ATOM, BOOL_TRUE_ATOM if value else BOOL_FALSE_ATOM]

    def pack_none(self, value):
        return [NONE_ATOM]

    def pack_enum(self, value):
        return [ENUM_ATOM, reflect.canonical_name(value), value.name]

    def pack_tuple(self, values):
        return [TUPLE_ATOM] + values

    def pack_list(self, values):
        return [LIST_ATOM] + values

    def pack_dict(self, items):
        return [DICT_ATOM] + items

    def pack_set(self, values):
        return [SET_ATOM] + values

    def pack_reference(self, value):
        return [REFERENCE_ATOM] + value

    def pack_dereference(self, value):
        return [DEREFERENCE_ATOM, value]

    def pack_type(self, value):
        return [CLASS_ATOM, reflect.canonical_name(value)]

    def pack_external(self, value):
        return [EXTERNAL_ATOM] + value

    def pack_frozen_external(self, value):
        content, = value
        return content

    def pack_frozen_instance(self, value):
        content, = value
        return content

    def pack_frozen_function(self, value):
        return reflect.canonical_name(value)

    pack_frozen_method = pack_frozen_function
    pack_frozen_builtin = pack_frozen_function


class Unserializer(base.Unserializer):
    '''Unserialize a structure serialized with L{sexp.Serializer}.'''

    pass_through_types = set([str, int, long, float])

    def __init__(self, pre_converter=None, registry=None, externalizer=None,
                 converter_caps=None,
                 source_ver=None, target_ver=None):
        base.Unserializer.__init__(self, pre_converter=pre_converter,
                                   registry=registry,
                                   externalizer=externalizer,
                                   converter_caps=converter_caps,
                                   source_ver=source_ver,
                                   target_ver=target_ver)

    ### Overridden Methods ###

    def analyse_data(self, data):
        vtype = type(data)

        if vtype is not list:
            return None

        type_name = data[0]
        # We assume that if it's nothing we know about, it's an instance
        default = (type_name, Unserializer.unpack_instance)
        return self._unpackers.get(type_name, default)

    ### Private Methods ###

    def unpack_instance(self, data, *args):
        type_name, value = data
        return self.restore_instance(type_name, value, *args)

    def unpack_unicode(self, data):
        _, value = data
        if not isinstance(value, (bytes, str)):
            raise TypeError("Invalid %s value type: %r"
                            % (UNICODE_ATOM, value))
        return value.decode(UNICODE_FORMAT_ATOM)

    def unpack_bool(self, data):
        _, value = data
        if value == BOOL_TRUE_ATOM:
            return True
        if value == BOOL_FALSE_ATOM:
            return False
        raise ValueError("Invalid %s value: %r" % (BOOL_ATOM, value))

    def unpack_none(self, data):
        _, = data
        return None

    def unpack_enum(self, data):
        _, enum_name, enum_value = data
        enum_class = self.restore_type(enum_name)
        return enum_class[enum_value]

    def unpack_external(self, data):
        _, ext_id = data
        return self.restore_external(ext_id)

    def unpack_type(self, data):
        _, type_name, = data
        return self.restore_type(type_name)

    def unpack_reference(self, data):
        _, refid, value = data
        return self.restore_reference(refid, value)

    def unpack_dereference(self, data):
        _, refid = data
        return self.restore_dereference(refid)

    def unpack_tuple(self, data):
        return tuple([self.unpack_data(d) for d in data[1:]])

    def unpack_list(self, container, data):
        container.extend([self.unpack_data(d) for d in data[1:]])

    def unpack_set(self, container, data):
        container.update([self.unpack_data(d) for d in data[1:]])

    def unpack_dict(self, container, data):
        container.update([(self.unpack_data(k), self.unpack_data(v))
                          for k, v in data[1:]])

    _unpackers = {UNICODE_ATOM: (None, unpack_unicode),
                  BOOL_ATOM: (None, unpack_bool),
                  NONE_ATOM: (None, unpack_none),
                  TUPLE_ATOM: (None, unpack_tuple),
                  CLASS_ATOM: (None, unpack_type),
                  ENUM_ATOM: (None, unpack_enum),
                  EXTERNAL_ATOM: (None, unpack_external),
                  REFERENCE_ATOM: (None, unpack_reference),
                  DEREFERENCE_ATOM: (None, unpack_dereference),
                  LIST_ATOM: (list, unpack_list),
                  SET_ATOM: (set, unpack_set),
                  DICT_ATOM: (dict, unpack_dict)}
