# -*- coding: utf-8 -*-

from __future__ import absolute_import

from serialization.common import error

try:
    import msgpack
except ImportError:
    raise error.SerializeRequirementError(
        'Install `python-msgpack` before use this serializer'
    )

from serialization import sexp


class Serializer(sexp.Serializer):
    pass


class Unserializer(sexp.Unserializer):
    pass


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
