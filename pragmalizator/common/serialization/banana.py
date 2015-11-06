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

from cStringIO import StringIO

from twisted.spread import banana

from pragmalizator.common import reflect
from pragmalizator.common.serialization import sexp, base
from pragmalizator.interface.serialization import Capabilities


class BananaCodec(object):

    def __init__(self):
        self._banana = banana.Banana()
        self._banana.connectionMade()
        self._banana._selectDialect("pb") # More compact

    def encode(self, lst):
        io = StringIO()
        self._banana.transport = io
        self._banana.sendEncoded(lst)
        return io.getvalue()

    def decode(self, data):
        heap = []
        self._banana.expressionReceived = heap.append
        try:
            self._banana.dataReceived(data)
        finally:
            self._banana.buffer = ''
            del self._banana.expressionReceived
        return heap[0]


BANANA_CONVERTER_CAPS = set([Capabilities.method_values,
                               Capabilities.function_values,
                               ])


METHOD_ATOM = '.banana_method'
FUNCTION_ATOM = '.banana_function'


class Serializer(sexp.Serializer, BananaCodec):

    def __init__(self, externalizer=None, source_ver=None, target_ver=None):
        sexp.Serializer.__init__(
            self, externalizer=externalizer,
            converter_caps=base.DEFAULT_CONVERTER_CAPS | BANANA_CONVERTER_CAPS,
            freezer_caps=base.DEFAULT_FREEZER_CAPS | BANANA_CONVERTER_CAPS,
                                 source_ver=source_ver, target_ver=target_ver)
        BananaCodec.__init__(self)

    def pack_method(self, data):
        if self._externalizer is not None:
            extid = self._externalizer.identify(data)
            if extid is None:
                raise TypeError("Failed to serialize %r. Can only serialize "
                                "methods of values known to externalizer.")
            return [METHOD_ATOM, extid, data.__name__]

    def pack_function(self, data):
        return [FUNCTION_ATOM, reflect.canonical_name(data)]

    ### Overridden Methods ###

    def post_convertion(self, data):
        return self.encode(data)


class Unserializer(sexp.Unserializer, BananaCodec):

    def __init__(self, registry=None, externalizer=None,
                 source_ver=None, target_ver=None):
        sexp.Unserializer.__init__(self, registry=registry,
                                   converter_caps=BANANA_CONVERTER_CAPS,
                                   externalizer=externalizer,
                                   source_ver=source_ver,
                                   target_ver=target_ver)
        BananaCodec.__init__(self)

    ### Overridden Methods ###

    def pre_convertion(self, data):
        return self.decode(data)

    def analyse_data(self, data):
        if isinstance(data, list) and data[0] == METHOD_ATOM:
            instance = self._externalizer.lookup(data[1])
            if instance is None:
                raise ValueError(
                    "Failed to lookup the externalize object: %r" %
                    (data[1], ))
            return getattr(instance, data[2])

        if isinstance(data, list) and data[0] == FUNCTION_ATOM:
            return reflect.named_object(data[1])

        return super(Unserializer, self).analyse_data(data)


def serialize(value):
    global _serializer
    return _serializer.convert(value)


def freeze(value):
    global _serializer
    return _serializer.freeze(value)


def unserialize(data):
    global _unserializer
    return _unserializer.convert(data)


### Private Stuff ###

_serializer = Serializer()
_unserializer = Unserializer()
