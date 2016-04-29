# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

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
import itertools
import types


from past.types import long, unicode

from six import with_metaclass, PY3
import pytest

from builtins import range
from builtins import object

from zope.interface import Interface
from zope.interface.declarations import implementer
from zope.interface.interface import InterfaceClass

try:
    from twisted.persisted.crefutil import NotKnown
except:
    NotKnown = None

import serialization
from serialization import base
from serialization.interface import Capabilities, ISnapshotable, ISerializable


def qual(clazz):
    """Return full import path of a class."""
    return clazz.__module__ + '.' + clazz.__name__


if PY3:
    type_of__dict__ = types.MappingProxyType
    skipped_in__dict__ = ('__dict__', '__weakref__')
else:
    type_of__dict__ = types.DictProxyType
    skipped_in__dict__ = tuple()


class DummyEnum(enum.Enum):
    a, b, c = list(range(3))


class DummyInterface(Interface):
    pass


@implementer(ISnapshotable)
class SnapshotableDummy(object):

    def __init__(self, value):
        self.value = value

    # ## ISnapshotable ###

    def snapshot(self):
        return self.value


@serialization.register
class SerializableDummy(serialization.Serializable):
    '''Simple dummy class that implements various serialization scheme.'''

    def __init__(self):
        self.str = "dummy"
        self.unicode = u"dummy"
        self.int = 42
        self.long = 2 ** 66
        self.float = 3.1415926
        self.bool = True
        self.none = None
        self.list = [1, 2, 3]
        self.tuple = (1, 2, 3)
        self.set = set([1, 2, 3])
        self.dict = {1: 2, 3: 4}
        self.ref = None

    def __repr__(self):
        return "<%s: %s>" % (type(self).__name__, repr(self.__dict__))

    def __eq__(self, value):
        return (value is self
                or (self.str == value.str
                    and self.unicode == value.unicode
                    and self.int == value.int
                    and self.long == value.long
                    and abs(self.float - value.float) < 0.00000001
                    and self.bool == value.bool
                    and self.none == value.none
                    and self.list == value.list
                    and self.tuple == value.tuple
                    and self.set == value.set
                    and self.dict == value.dict
                    and self.ref == value.ref))


@serialization.register
class NotReferenceableDummy(serialization.Serializable):

    referenceable = False

    def __init__(self, value=42):
        self.value = value

    def __repr__(self):
        return "<%s: %s>" % (type(self).__name__, repr(self.__dict__))

    def __eq__(self, value):
        return (value is self or (self.value == value.value))


class TestTypeSerializationDummy(object):
    pass


class MetaTestTypeSerializationDummy(type):
    pass


class TestTypeSerializationDummyWithMeta(
        with_metaclass(MetaTestTypeSerializationDummy, object)):
    __metaclass_save_equal_hack__ = MetaTestTypeSerializationDummy
    # our `safe_equal` use `__dict__` and `__metaclass__` is in
    # this dict so we need some other __other_field__ to ident it


class ConverterTestHelper(object):
    '''Base classes for convert test cases.

    Sub-classes should override convertion_table() to return
    an iterator on a list of records containing::

        (INPUT_TYPE, [POSSIBLE_INPUT_VALUES],
         OUTPUT_TYPE, [POSSIBLE_OUTPUT_VALUES],
         SHOULD_BE_COPIED)

    To test a pair of converters, one should inherit from this
    base class and override convertion_table() for the pair of
    converters. Then create a class for each conversion
    way inheriting from it, one with the SerializerMixin
    and one with UnserializerMixin.

    These classes have to override setUp() and initialize some attributes:

      - self.serializer : the L{IConverter} to serialize.
      - self.unserializer : the L{IConverter} to unserialize or None.

    Child class can use checkSymmetry() to check the symmetry to check
    symmetry with other serializer/unserializer..

    See test_common_serialization_pytree.py for examples.
    '''

    def __init__(self):
        self.ext_val = SerializableDummy()
        self.ext_val.str = "externalized"  # Just for it be different
        self.ext_snap_val = SnapshotableDummy(42)
        self.externalizer = base.Externalizer()
        self.externalizer.add(self.ext_val)
        self.externalizer.add(self.ext_snap_val)

    def check_unserialization(
            self, serializer, unserializer, convertion_table):

        def inverter(gen):
            while True:
                record = next(gen)
                if len(record) == 5:
                    t1, v1, t2, v2, c = record
                    yield t2, v2, t1, v1, c
                elif len(record) == 7:
                    t1, v1, a1, t2, v2, a2, c = record
                    yield t2, v2, a2, t1, v1, a1, c
                else:
                    pytest.fail(
                        "Unexpected conversion table record:\nRECORD: %r"
                        % (record, ))

        capabilities = unserializer.converter_capabilities
        table = convertion_table(capabilities, False)
        self._check_convertion(
            inverter(table), unserializer.convert, capabilities=capabilities)

    def check_serialization(self, serializer, convertion_table):
        capabilities = serializer.converter_capabilities
        table = convertion_table(capabilities, False)
        self._check_convertion(
            table, serializer.convert, capabilities=capabilities)

    def check_freezing(self, serializer, convertion_table):
        capabilities = serializer.freezer_capabilities
        table = convertion_table(capabilities, True)
        self._check_convertion(
            table, serializer.freeze, capabilities=capabilities)

    def check_symmetry(self, serializer, unserializer):
        cap1 = unserializer.converter_capabilities
        cap2 = serializer.converter_capabilities
        capabilities = cap1.intersection(cap2)
        self._check_symmetry(
            serializer.convert, unserializer.convert,
            capabilities=capabilities)

    def _check_convertion(self, table, converter, capabilities=None):
        # If int and long types are considered equals
        generic_int = (capabilities is not None
                       and Capabilities.int_values in capabilities
                       and Capabilities.long_values in capabilities)

        for record in table:
            if len(record) == 5:
                _t1, v1, t2, v2, c = record
                values = v1
                exp_type = t2
                exp_values = v2
                should_be_copied = c
            elif len(record) == 7:
                _t1, v1, _a1, t2, v2, a2, c = record
                values = v1
                exp_type = t2
                exp_values = v2 + a2
                should_be_copied = c
            else:
                pytest.fail(
                    "Unexpected conversion table record:\nRECORD: %r"
                    % (record, ))

            exp_types, exp_type_names = self._exp_types(exp_type)

            for value in values:
                result = converter(value)

                # Check type
                assert isinstance(result, exp_types)

                # Check it's a copy, if required
                if should_be_copied:
                    assert value is not result

                # Look for an expected value
                for expected in exp_values:
                    # For each possible expected values
                    if self.safe_equal(expected, result, generic_int):
                        break
                else:
                    pytest.fail(
                        "Value not converted to one of the expected "
                        "values:\nVALUE:    %r\nRESULT:   %r\n%s"
                        % (value, result,
                            "\n".join(["EXPECTED: " + repr(v)
                                        for v in exp_values])))

    def _check_symmetry(
            self, serializer, deserializer, capabilities=None, strict=True):

        if capabilities is None:
            capabilities = base.DEFAULT_CONVERTER_CAPS

        # If int and long types are considered equals
        generic_int = (Capabilities.int_values in capabilities
                       and Capabilities.long_values in capabilities)

        for exp_type, values, must_change in self.symmetry_table(capabilities):
            exp_types, exp_type_names = self._exp_types(exp_type)
            for value in values:
                assert issubclass(type(value), exp_types)
                data = serializer(value)
                result = deserializer(data)
                assert issubclass(type(result), exp_types)

                for v in values:
                    if self.safe_equal(result, v, generic_int, strict=strict):
                        expected = v
                        break
                else:
                    pytest.fail(
                        "Value not one of the expected values:\n"
                        "VALUE:    %r\nRESULT:   %r\n%s" % (
                            value, result,
                            "\n".join(["EXPECTED: " + repr(v)
                                       for v in values])))
                if must_change:
                    assert_equal_but_different(
                        result, expected, 0, {}, {}, strict=strict)

    def symmetry_table(self, capabilities):
        valdesc = [(Capabilities.int_values, Capabilities.int_keys,
                    [int, long], [0, -42, 42]),
                   (Capabilities.long_values, Capabilities.long_keys,
                    [int, long], [long(0)]),
                   (Capabilities.long_values, Capabilities.long_keys,
                    long, [-2 ** 66, 2 ** 66]),
                   (Capabilities.float_values, Capabilities.float_keys,
                    float, [0.0, 3.14159, -3.14159, 1.23145e23, 1.23145e-23]),
                   (Capabilities.bytes_values, Capabilities.str_keys,
                    str, ["", "spam"]),
                   # May not be valid for keys
                   (Capabilities.bytes_values, None,
                    str, ["\x00", "\n", "\xFF"]),
                   (Capabilities.unicode_values, Capabilities.unicode_keys,
                    unicode, [u"", u"hétérogénéité", u"\x00\xFF\n"]),
                   (Capabilities.bool_values, Capabilities.bool_keys,
                    bool, [True, False]),
                   (Capabilities.none_values, Capabilities.none_keys,
                    type(None), [None])]

        type_values = []
        if Capabilities.meta_types in capabilities:
            type_values.append(TestTypeSerializationDummyWithMeta)
            type_values.append(SerializableDummy)
        if Capabilities.new_style_types in capabilities:
            type_values.append(int)
            from datetime import datetime
            type_values.append(datetime)
            type_values.append(TestTypeSerializationDummy)

        if type_values:
            valdesc.append((Capabilities.type_values, Capabilities.type_keys,
                            type, type_values))
            valdesc.append((Capabilities.type_values, Capabilities.type_keys,
                            InterfaceClass, [DummyInterface]))

        def iter_values(desc):
            for cap, _, value_type, values in valdesc:
                if cap in capabilities:
                    for value in values:
                        yield value_type, value, False

        def iter_keys(desc):
            for _, cap, value_type, values in valdesc:
                if cap in capabilities:
                    for value in values:
                        yield value_type, value, False

        def cleanup_dummy_instance(o):
            if Capabilities.int_values not in capabilities:
                del o.int
            if Capabilities.long_values not in capabilities:
                del o.long
            if Capabilities.float_values not in capabilities:
                del o.float
            if Capabilities.bytes_values not in capabilities:
                del o.str
            if Capabilities.unicode_values not in capabilities:
                del o.unicode
            if Capabilities.bool_values not in capabilities:
                del o.bool
            if Capabilities.none_values not in capabilities:
                del o.none
            if Capabilities.tuple_values not in capabilities:
                del o.tuple
            if Capabilities.list_values not in capabilities:
                del o.list
            if (Capabilities.set_values not in capabilities
                    or Capabilities.int_keys not in capabilities):
                del o.set
            if (Capabilities.dict_values not in capabilities
                    or Capabilities.int_keys not in capabilities):
                del o.dict
            return o

        def iter_instances(desc):
            # Default instance
            o = SerializableDummy()
            yield SerializableDummy, cleanup_dummy_instance(o), True
            # Modified instance
            o = SerializableDummy()

            del o.int
            del o.none

            o.str = "spam"
            o.unicode = "fúúúú"
            o.long = 2 ** 44
            o.float = 2.7182818284
            o.bool = False
            o.list = ['a', 'b', 'c']
            o.tuple = ('d', 'e', 'f')
            o.set = set(['g', 'h', 'i'])
            o.dict = {'j': 1, 'k': 2, 'l': 3}

            yield SerializableDummy, cleanup_dummy_instance(o), True

            yield NotReferenceableDummy, NotReferenceableDummy(), True

        def iter_externals(desc):
            yield SerializableDummy, self.ext_val, False

        def iter_all_values(desc, stop=False, immutable=False):
            values = [v for _, v, _ in iter_values(desc)]
            if not immutable:
                if Capabilities.instance_values in capabilities:
                    values += [v for _, v, _ in iter_instances(desc)]
                if Capabilities.enum_values in capabilities:
                    values += [v for _, v, _ in iter_enums(desc)]
            if not stop:
                if Capabilities.tuple_values in capabilities:
                    values += [v for _, v, _ in
                               iter_tuples(desc, True, immutable)]
                if not immutable:
                    if Capabilities.list_values in capabilities:
                        values += [v for _, v, _ in iter_lists(desc, True)]
                    if Capabilities.set_values in capabilities:
                        values += [v for _, v, _ in iter_sets(desc, True)]
                    if Capabilities.dict_values in capabilities:
                        values += [v for _, v, _ in iter_dicts(desc, True)]
            return values

        def iter_all_keys(desc, stop=False):
            values = [v for _, v, _ in iter_keys(desc)]
            if Capabilities.enum_keys in capabilities:
                values += [v for _, v, _ in iter_enums(desc)]
            if not stop:
                if Capabilities.tuple_keys in capabilities:
                    values += [v for _, v, _ in iter_tuples(desc, True, True)]
            return values

        def iter_enums(desc):
            # Because enums cannot be compared with anything else
            # we can't put it in the description table
            yield DummyEnum, DummyEnum.a, False
            yield DummyEnum, DummyEnum.c, False

        def iter_tuples(desc, stop=False, immutable=False):
            yield tuple, (), False  # Exception for empty tuple singleton
            # A tuple for each possible values
            for v in iter_all_values(desc, stop, immutable):
                yield tuple, tuple([v]), True
            # One big tuple with everything supported in it
            yield tuple, tuple(iter_all_values(desc, stop, immutable)), True

        def iter_lists(desc, stop=False):
            yield list, [], True
            # A list for each possible values
            for v in iter_all_values(desc, stop):
                yield list, [v], True
            # One big list with everything supported in it
            yield list, iter_all_values(desc, stop), True

        def iter_sets(desc, stop=False):
            yield set, set([]), True
            # A set for each possible values
            for v in iter_all_keys(desc, stop):
                yield set, set([v]), True
            # Enums cannot be mixed with other values
            yield (set, set([v for v in iter_all_keys(desc, stop)
                             if isinstance(v, enum.Enum)]), True)
            # One big set with everything supported in it
            yield (set, set([v for v in iter_all_keys(desc, stop)
                             if not isinstance(v, enum.Enum)]), True)

        def iter_dicts(desc, stop=False):
            yield dict, {}, True
            # Enums cannot be mixed with other values
            d = {}
            for k in iter_all_keys(desc, stop):
                if isinstance(k, enum.Enum):
                    d[k] = None
            yield dict, d, True
            # Big dicts for every supported values and keys
            values = iter(iter_all_values(desc, stop))
            done = False
            while not done:
                d = {}
                for k in iter_all_keys(desc, stop):
                    if not isinstance(k, enum.Enum):
                        try:
                            v = next(values)
                        except StopIteration:
                            # Loop back to the first value
                            values = iter(iter_all_values(desc, stop))
                            v = next(values)  # At least there is one value
                            done = True
                        d[k] = v
                yield dict, d, True

        def iter_all(desc):
            iterators = [iter_values(desc)]
            if Capabilities.enum_values in capabilities:
                iterators.append(iter_enums(desc))
            if Capabilities.instance_values in capabilities:
                iterators.append(iter_instances(desc))
            if Capabilities.tuple_values in capabilities:
                iterators.append(iter_tuples(desc))
            if Capabilities.list_values in capabilities:
                iterators.append(iter_lists(desc))
            if Capabilities.set_values in capabilities:
                iterators.append(iter_sets(desc))
            if Capabilities.dict_values in capabilities:
                iterators.append(iter_dicts(desc))
            if Capabilities.external_values in capabilities:
                iterators.append(iter_externals(desc))
            return itertools.chain(*iterators)

        for record in iter_all(valdesc):
            value_type, value, should_mutate = record
            yield value_type, [value], should_mutate

        if Capabilities.circular_references in capabilities:
            # get supported values, keys and referencable
            values = iter_values(valdesc)
            _, X, _ = next(values)
            _, Y, _ = next(values)

            keys = iter_keys(valdesc)
            _, K, _ = next(keys)
            _, L, _ = next(keys)

            if Capabilities.list_values in capabilities:
                Z = [X, Y]
            elif Capabilities.tuple_values in capabilities:
                Z = (X, Y)
            elif Capabilities.set_values in capabilities:
                Z = set([X, Y])
            elif Capabilities.dict_values in capabilities:
                Z = dict([X, Y])
            else:
                self.fail("Converter support circular references but do not "
                          "supporte any referencable types")

            if Capabilities.list_values in capabilities:
                # Reference in list
                yield list, [[Z, Z]], True
                yield list, [[Z, [Z, [Z], Z], Z]], True

                # List self-references
                a = []
                a.append(a)
                yield list, [a], True

                a = []
                b = [a]
                a.append(b)
                yield list, [b], True

            if Capabilities.tuple_values in capabilities:
                # Reference in tuple
                yield tuple, [(Z, Z)], True
                yield tuple, [(Z, (Z, (Z, ), Z), Z)], True

            if Capabilities.dict_values in capabilities:
                # Reference in dictionary value
                yield dict, [{K: Z, L: Z}], True
                yield dict, [{K: Z, L: {L: Z, K: {K: Z}}}], True

                # Dictionary self-references
                a = {}
                a[K] = a
                yield dict, [a], True

                a = {}
                b = {K: a}
                a[K] = b
                yield dict, [a], True

                if (Capabilities.tuple_keys in capabilities
                        and Capabilities.list_values in capabilities):
                    a = (K, L)

                    # Dereference in dictionary keys.
                    yield list, [[a, {a: X}]], True

                    # Reference in dictionary keys.
                    yield list, [[{a: Y}, a]], True

                    # Multiple reference in dictionary keys
                    a = (K, L)
                    yield dict, [{(K, a): X, (L, a): Y}], True

            if (Capabilities.set_values in capabilities
                    and Capabilities.tuple_keys in capabilities
                    and Capabilities.list_values in capabilities):

                a = (K, L)
                # Dereference in set.
                yield list, [[a, set([a])]], True

                # Reference in set.
                yield list, [[set([a]), a]], True

                # Multiple reference in set
                b = set([(K, a), (L, a)])
                yield set, [b], True

            if (Capabilities.tuple_values in capabilities
                    and Capabilities.list_values in capabilities
                    and Capabilities.dict_values in capabilities
                    and Capabilities.tuple_keys in capabilities
                    and Capabilities.list_values in capabilities):

                # Complex structure
                a = (K, L)
                b = (a, )
                b2 = set(b)
                c = (a, b)
                c2 = {a: b2, b: c}
                d = (a, b, c)
                d2 = [a, b2, c2]
                e = (b, c, d)
                e2 = [b2, c2, e]
                c2[e] = e2  # Make a cycle
                yield dict, [{b: b2, c: c2, d: d2, e: e2}], True

            if Capabilities.instance_values in capabilities:
                # complex references in instances
                o1 = SerializableDummy()
                o2 = SerializableDummy()
                o3 = SerializableDummy()

                # remove unsupported attributes
                o1 = cleanup_dummy_instance(o1)
                o2 = cleanup_dummy_instance(o2)
                o3 = cleanup_dummy_instance(o3)

                o1.dict = {K: X}
                o2.tuple = (X, )
                o3.list = [Y]

                o1.ref = o2
                o2.ref = o1
                o3.ref = o3
                o1.list = o3.list
                o2.dict = o1.dict
                o3.tuple = o2.tuple

                yield SerializableDummy, [o1], True
                yield SerializableDummy, [o2], True
                yield SerializableDummy, [o3], True

                if Capabilities.list_values in capabilities:
                    yield list, [[o1, o2]], True
                    yield list, [[o2, o1]], True
                    yield list, [[o1, o3]], True
                    yield list, [[o3, o1]], True
                    yield list, [[o2, o3]], True
                    yield list, [[o3, o2]], True
                    yield list, [[o1, o2, o3]], True
                    yield list, [[o3, o1, o2]], True

    def safe_equal(self, a, b, generic_int=True, strict=False):
        '''Circular references safe comparator.
        The two values must have the same internal references,
        meaning if a contains multiple references to the same
        object, b should equivalent values should be references
        too but do not need to be references to the same object,
        the object just have to be equals.'''
        return self._safe_equal(a, b, 0, {}, {}, generic_int, strict=strict)

    # ## Private Methods ###

    def _exp_types(self, val):
        if isinstance(val, (list, tuple)):
            assert len(val) > 0
            names = [t.__name__ for t in val]
            if len(names) == 1:
                type_names = names[0]
            else:
                type_names = " or ".join([", ".join(names[:-1]), names[-1]])
            return tuple(val), type_names
        return (val, ), val.__name__

    def _safe_equal(self, a, b, idx, arefs, brefs, gint, is__dict__=False,
                    strict=False):
        if not strict:
            a, b = _get_resolved_dereference(a, b)

        if a is b:
            return True

        if not (isinstance(a, type(b))
                or isinstance(b, type(a))):
            if type(a) != type(b):
                if not (gint and isinstance(a, (int, long))
                        and isinstance(b, (int, long))):
                    return False

        if isinstance(a, float):
            return abs(a - b) < 0.000001

        if isinstance(a, (int, long, bytes, unicode, bool, type(None))):
            return a == b

        aid = id(a)
        bid = id(b)

        if aid in arefs:
            # first value is a reference, check the other value is too
            if bid not in brefs:
                return False
            # Check the two reference the same value inside the structure
            return arefs[aid] == brefs[bid]

        if bid in brefs:
            return False

        arefs[aid] = idx
        brefs[bid] = idx

        if isinstance(a, (tuple, list)):
            if len(a) != len(b):
                return False
            for v1, v2 in zip(a, b):
                if not self._safe_equal(v1, v2, idx + 1, arefs, brefs, gint):
                    return False
                idx += 1
            return True

        if isinstance(a, set):
            if len(a) != len(b):
                return False
            for k1 in a:
                for k2 in b:
                    # We keep a copy of the reference dictionaries
                    # because if the comparison fail we don't want to pollute
                    # them with invalid references
                    acopy = dict(arefs)
                    bcopy = dict(brefs)
                    if self._safe_equal(k1, k2, idx + 1, acopy, bcopy, gint):
                        arefs.update(acopy)
                        brefs.update(bcopy)
                        break
                else:
                    # Not equal key found in b
                    return False
                idx += 1
            return True

        if isinstance(a, (dict, type_of__dict__)):
            if len(a) != len(b):
                return False
            for k1, v1 in a.items():
                # skipping this elements in __dict__
                if is__dict__ and k1 in skipped_in__dict__:
                    continue
                for k2, v2 in b.items():
                    if is__dict__ and k1 in skipped_in__dict__:
                        continue
                    # We keep a copy of copy of the reference dictionaries
                    # because if the comparison fail we don't want to pollute
                    # them with invalid references
                    acopy = dict(arefs)
                    bcopy = dict(brefs)
                    if self._safe_equal(k1, k2, idx + 1, acopy, bcopy, gint):
                        if not self._safe_equal(v1, v2, idx + 2,
                                                arefs, brefs, gint):
                            return False
                        arefs.update(acopy)
                        brefs.update(bcopy)
                        break
                else:
                    # Not key found
                    return False
                idx += 2
            return True

        if hasattr(a, "__dict__"):
            return self._safe_equal(a.__dict__, b.__dict__,
                                    idx + 1, arefs, brefs, gint,
                                    is__dict__=True)

        if hasattr(a, "__slots__"):
            for attr in a.__slots__:
                v1 = getattr(a, attr)
                v2 = getattr(b, attr)
                if not self._safe_equal(v1, v2, idx + 1, arefs, brefs, gint):
                    return False
            return True
        pytest.fail("I don't know how to compare %r and %r" % (a, b))


def _get_resolved_dereference(*objs):
    r = []
    for obj in objs:
        if (NotKnown is not None and isinstance(obj, NotKnown) and
            obj.resolved >= 1):
            r.append(obj.resolvedObject)
        else:
            r.append(obj)
    return r


def assert_equal_but_different(
        value, expected, idx, valids, expids, strict=True):
    '''
    idx is used to identify every values uniquely to be able to verify
    references are made to the same value, valids and expids are
    dictionaries with instance id() for key and idx for value.
    Types and interfaces are assumed to be immutable atoms.'''

    # Only check references for type that can be referenced.
    # Let the immutable type do what they want, sometime strings
    # are interned sometime no, we don't care.
    basic_types = (int, long, float, bool, str, unicode, type(None))
    if not isinstance(expected, basic_types):
        # Get unique instance identifiers
        if not strict:
            value, expected = _get_resolved_dereference(value, expected)
        expid = id(expected)
        valid = id(value)

        if expid in expids:
            # Expected value is a reference, check the other value is too
            assert valid in valids
            # Check the two reference the same value inside the structure
            assert valids[valid] == expids[expid]
            return idx

        # Check the other value is not a reference if it wasn't expected
        assert valid not in valids

        # Store the instance identifiers for later checks
        expids[expid] = idx
        valids[valid] = idx

    if expected is None:
        assert expected == value
    elif isinstance(expected, (list, tuple)):
        if expected != ():  # Special case for tuple singleton
            assert value is not expected

        assert len(expected) == len(value)
        for exp, val in zip(expected, value):
            idx = assert_equal_but_different(
                val, exp, idx + 1, valids, expids, strict=strict)
    elif isinstance(expected, set):
        assert len(expected) == len(value)
        for exp in expected:
            assert exp in value
            val = [v for v in value if v == exp][0]
            idx = assert_equal_but_different(
                val, exp, idx + 1, valids, expids, strict=strict)
    elif isinstance(expected, dict):
        assert len(expected) == len(value)
        for exp_key, exp_val in expected.items():
            assert exp_key in value
            val_key = [k for k in value if k == exp_key][0]
            val_val = value[val_key]
            idx = assert_equal_but_different(
                val_key, exp_key, idx + 1, valids, expids, strict=strict)
            idx = assert_equal_but_different(
                val_val, exp_val, idx + 1, valids, expids, strict=strict)
    elif isinstance(value, float):
        assert round(value - expected, 7) == 0
    elif isinstance(value, (int, long, bool, str, unicode,
                            type, InterfaceClass, enum.Enum)):
        assert value == expected
    else:
        assert expected is not value
        if ISerializable.providedBy(expected):
            assert ISerializable.providedBy(value)
        idx = assert_equal_but_different(
            value.__dict__, expected.__dict__, idx + 1, valids, expids,
            strict=strict)
    return idx
