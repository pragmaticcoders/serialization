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

import types
from past.types import long, unicode
from six import with_metaclass

import pytest
from zope.interface import Interface
from zope.interface.interface import InterfaceClass

from serialization import pytree, base, reflect
import serialization

from . import utils


@serialization.register
class DummyClass(serialization.Serializable):

    def dummy_method(self):
        pass

    @serialization.freeze_tag('dummy_tag')
    def dummer_method(self):
        pass


def dummy_function():
    pass


class DummyInterface(Interface):
    pass


@serialization.register
class DummySerializable(serialization.Serializable):

    def __init__(self, value):
        self.value = value
        self._restored = False

    def restored(self):
        self._restored = True


@serialization.register
class DummyImmutableSerializable(serialization.ImmutableSerializable):

    def __init__(self, value):
        self.value = value
        self._restored = False

    def restored(self):
        self._restored = True


class Versioned(with_metaclass(
        type("MetaAv1", (type(serialization.Serializable),
                         type(base.VersionAdapter)), {}),
        serialization.Serializable, base.VersionAdapter)):
    pass


class Av1(Versioned):

    type_name = "A"

    def __init__(self):
        self.foo = "42"


class Av2(Av1):
    type_name = "A"

    def __init__(self):
        self.foo = 42

    @staticmethod
    def upgrade_to_2(snapshot):
        snapshot["foo"] = int(snapshot["foo"])
        return snapshot

    @staticmethod
    def downgrade_to_1(snapshot):
        snapshot["foo"] = str(snapshot["foo"])
        return snapshot


class Av3(Av2):
    type_name = "A"

    def __init__(self):
        self.bar = 42

    @staticmethod
    def upgrade_to_3(snapshot):
        snapshot["bar"] = snapshot["foo"]
        del snapshot["foo"]
        return snapshot

    @staticmethod
    def downgrade_to_2(snapshot):
        snapshot["foo"] = snapshot["bar"]
        del snapshot["bar"]
        return snapshot


class Bv1(Versioned):
    type_name = "B"

    def __init__(self):
        self.a = Av1()
        self.b = Av1()
        self.c = Av1()
        self.a.foo = "1"
        self.b.foo = "2"
        self.c.foo = "3"


class Bv2(Bv1):
    type_name = "B"

    def __init__(self):
        a = Av2()
        b = Av2()
        c = Av2()
        a.foo = 1
        b.foo = 2
        c.foo = 3
        self.values = [a, b, c]

    @staticmethod
    def upgrade_to_2(snapshot):
        a = snapshot["a"]
        b = snapshot["b"]
        c = snapshot["c"]
        del snapshot["a"]
        del snapshot["b"]
        del snapshot["c"]
        snapshot["values"] = [a, b, c]
        return snapshot

    @staticmethod
    def downgrade_to_1(snapshot):
        a, b, c = snapshot["values"]
        del snapshot["values"]
        snapshot["a"] = a
        snapshot["b"] = b
        snapshot["c"] = c
        return snapshot


class Bv3(Bv2):
    type_name = "B"

    def __init__(self):
        a = Av3()
        b = Av3()
        c = Av3()
        a.bar = 1
        b.bar = 2
        c.bar = 3
        self.values = {"a": a, "b": b, "c": c}

    @staticmethod
    def upgrade_to_3(snapshot):
        a, b, c = snapshot["values"]
        snapshot["values"] = {"a": a, "b": b, "c": c}
        return snapshot

    @staticmethod
    def downgrade_to_2(snapshot):
        values = snapshot["values"]
        snapshot["values"] = [values["a"], values["b"], values["c"]]
        return snapshot


class TestPyTreeVersion(object):

    def adapt(self, value, registry, source_ver, inter_ver, target_ver):
        serializer = pytree.Serializer(
            source_ver=source_ver, target_ver=inter_ver)
        data = serializer.convert(value)
        unserializer = pytree.Unserializer(
            registry=registry, source_ver=inter_ver, target_ver=target_ver)
        return unserializer.convert(data)

    def test_simple_upgrades(self):
        r1 = serialization.Registry()
        r1.register(Av1)
        r2 = serialization.Registry()
        r2.register(Av2)
        r3 = serialization.Registry()
        r3.register(Av3)

        a1 = Av1()
        assert hasattr(a1, "foo")
        assert not hasattr(a1, "bar")
        assert a1.foo == "42"
        a1.foo = "18"

        a12 = self.adapt(a1, r2, 1, 1, 2)
        assert hasattr(a12, "foo")
        assert not hasattr(a12, "bar")
        assert a12.foo == 18

        a13 = self.adapt(a1, r3, 1, 1, 3)
        assert not hasattr(a13, "foo")
        assert hasattr(a13, "bar")
        assert a13.bar == 18

        a2 = Av2()
        assert hasattr(a2, "foo")
        assert not hasattr(a2, "bar")
        assert a2.foo == 42
        a2.foo = 23

        a23 = self.adapt(a2, r3, 2, 2, 3)
        assert not hasattr(a23, "foo")
        assert hasattr(a23, "bar")
        assert a23.bar == 23

    def test_simple_downgrade(self):
        r1 = serialization.Registry()
        r1.register(Av1)
        r2 = serialization.Registry()
        r2.register(Av2)
        r3 = serialization.Registry()
        r3.register(Av3)

        a3 = Av3()
        assert not hasattr(a3, "foo")
        assert hasattr(a3, "bar")
        assert a3.bar == 42
        a3.bar = 24

        a32 = self.adapt(a3, r2, 3, 2, 2)
        assert hasattr(a32, "foo")
        assert not hasattr(a32, "bar")
        assert a32.foo == 24

        a31 = self.adapt(a3, r2, 3, 2, 1)
        assert hasattr(a31, "foo")
        assert not hasattr(a31, "bar")
        assert a31.foo == "24"

        a31 = self.adapt(a3, r1, 3, 1, 1)
        assert hasattr(a31, "foo")
        assert not hasattr(a31, "bar")
        assert a31.foo == "24"

        a2 = Av2()
        assert hasattr(a2, "foo")
        assert not hasattr(a2, "bar")
        assert a2.foo == 42
        a2.foo = 18

        a21 = self.adapt(a2, r1, 2, 1, 1)
        assert hasattr(a21, "foo")
        assert not hasattr(a21, "bar")
        assert a21.foo == "18"

    def test_simple_down_up(self):
        r1 = serialization.Registry()
        r1.register(Av1)
        r2 = serialization.Registry()
        r2.register(Av2)
        r3 = serialization.Registry()
        r3.register(Av3)

        a2 = Av2()
        assert hasattr(a2, "foo")
        assert not hasattr(a2, "bar")
        assert a2.foo == 42
        a2.foo = 18

        a23 = self.adapt(a2, r3, 2, 1, 3)
        assert not hasattr(a23, "foo")
        assert hasattr(a23, "bar")
        assert a23.bar == 18

    def test_compound_upgrades(self):
        r1 = serialization.Registry()
        r1.register(Av1)
        r1.register(Bv1)
        r2 = serialization.Registry()
        r2.register(Av2)
        r2.register(Bv2)
        r3 = serialization.Registry()
        r3.register(Av3)
        r3.register(Bv3)

        b1 = Bv1()
        assert hasattr(b1, "a")
        assert hasattr(b1, "b")
        assert hasattr(b1, "c")
        assert not hasattr(b1, "values")
        assert b1.a.foo == "1"
        assert b1.b.foo == "2"
        assert b1.c.foo == "3"
        b1.a.foo = "4"
        b1.b.foo = "5"
        b1.c.foo = "6"

        b12 = self.adapt(b1, r2, 1, 1, 2)
        assert not hasattr(b12, "a")
        assert not hasattr(b12, "b")
        assert not hasattr(b12, "c")
        assert hasattr(b12, "values")
        assert isinstance(b12.values, list)
        assert b12.values[0].foo == 4
        assert b12.values[1].foo == 5
        assert b12.values[2].foo == 6

        b13 = self.adapt(b1, r3, 1, 1, 3)
        assert not hasattr(b13, "a")
        assert not hasattr(b13, "b")
        assert not hasattr(b13, "c")
        assert hasattr(b13, "values")
        assert isinstance(b13.values, dict)
        assert b13.values["a"].bar == 4
        assert b13.values["b"].bar == 5
        assert b13.values["c"].bar == 6

        b2 = Bv2()
        assert not hasattr(b2, "a")
        assert not hasattr(b2, "b")
        assert not hasattr(b2, "c")
        assert hasattr(b2, "values")
        assert isinstance(b2.values, list)
        assert b2.values[0].foo == 1
        assert b2.values[1].foo == 2
        assert b2.values[2].foo == 3
        b2.values[0].foo = 4
        b2.values[1].foo = 5
        b2.values[2].foo = 6

        b23 = self.adapt(b2, r3, 2, 2, 3)
        assert not hasattr(b23, "a")
        assert not hasattr(b23, "b")
        assert not hasattr(b23, "c")
        assert hasattr(b23, "values")
        assert isinstance(b23.values, dict)
        assert b23.values["a"].bar == 4
        assert b23.values["b"].bar == 5
        assert b23.values["c"].bar == 6

    def test_compound_downgrade(self):
        r1 = serialization.Registry()
        r1.register(Av1)
        r1.register(Bv1)
        r2 = serialization.Registry()
        r2.register(Av2)
        r2.register(Bv2)
        r3 = serialization.Registry()
        r3.register(Av3)
        r3.register(Bv3)

        b3 = Bv3()
        assert not hasattr(b3, "a")
        assert not hasattr(b3, "b")
        assert not hasattr(b3, "c")
        assert hasattr(b3, "values")
        assert isinstance(b3.values, dict)
        assert b3.values["a"].bar == 1
        assert b3.values["b"].bar == 2
        assert b3.values["c"].bar == 3
        b3.values["a"].bar = 4
        b3.values["b"].bar = 5
        b3.values["c"].bar = 6

        b32 = self.adapt(b3, r2, 3, 2, 2)
        assert not hasattr(b32, "a")
        assert not hasattr(b32, "b")
        assert not hasattr(b32, "c")
        assert hasattr(b32, "values")
        assert isinstance(b32.values, list)
        assert b32.values[0].foo == 4
        assert b32.values[1].foo == 5
        assert b32.values[2].foo == 6

        b32 = self.adapt(b3, r3, 3, 3, 2)
        assert not hasattr(b32, "a")
        assert not hasattr(b32, "b")
        assert not hasattr(b32, "c")
        assert hasattr(b32, "values")
        assert isinstance(b32.values, list)
        assert b32.values[0].foo == 4
        assert b32.values[1].foo == 5
        assert b32.values[2].foo == 6

        b31 = self.adapt(b3, r1, 3, 1, 1)
        assert hasattr(b31, "a")
        assert hasattr(b31, "b")
        assert hasattr(b31, "c")
        assert not hasattr(b31, "values")
        assert b31.a.foo == "4"
        assert b31.b.foo == "5"
        assert b31.c.foo == "6"

        b31 = self.adapt(b3, r2, 3, 2, 1)
        assert hasattr(b31, "a")
        assert hasattr(b31, "b")
        assert hasattr(b31, "c")
        assert not hasattr(b31, "values")
        assert b31.a.foo == "4"
        assert b31.b.foo == "5"
        assert b31.c.foo == "6"

        b2 = Bv2()
        assert not hasattr(b2, "a")
        assert not hasattr(b2, "b")
        assert not hasattr(b2, "c")
        assert hasattr(b2, "values")
        assert isinstance(b2.values, list)
        assert b2.values[0].foo == 1
        assert b2.values[1].foo == 2
        assert b2.values[2].foo == 3
        b2.values[0].foo = 4
        b2.values[1].foo = 5
        b2.values[2].foo = 6

        b21 = self.adapt(b2, r1, 2, 1, 1)
        assert hasattr(b21, "a")
        assert hasattr(b21, "b")
        assert hasattr(b21, "c")
        assert not hasattr(b21, "values")
        assert b21.a.foo == "4"
        assert b21.b.foo == "5"
        assert b21.c.foo == "6"


class TestGenericSerialization(object):

    @pytest.fixture
    def serializer(self, helper):
        return pytree.Serializer(externalizer=helper.externalizer)

    @pytest.fixture
    def unserializer(self, helper):
        return pytree.Unserializer(externalizer=helper.externalizer)

    def test_restored_call(self, unserializer, serializer):
        orig = DummySerializable(42)
        obj = unserializer.convert(serializer.convert(orig))
        assert type(orig) == type(obj)
        assert orig.value == obj.value
        assert obj._restored

        orig = DummyImmutableSerializable(42)
        obj = unserializer.convert(serializer.convert(orig))
        assert type(orig) == type(obj)
        assert orig.value == obj.value
        assert obj._restored

    def test_freezing_tags(self, serializer):
        instance = DummyClass()
        frozen = serializer.freeze(instance.dummer_method)
        assert 'dummy_tag' == frozen

    def test_not_referenceable(self, serializer):
        Klass = utils.NotReferenceableDummy
        Inst = pytree.Instance
        name = reflect.canonical_name(Klass)

        obj = Klass()
        data = serializer.convert([obj, obj])

        assert data == [
            Inst(name, {"value": 42}), Inst(name, {"value": 42})]

        data = serializer.freeze([obj, obj])
        assert data == [{"value": 42}, {"value": 42}]


class TestPyTreeConverters(object):

    @pytest.fixture
    def serializer(self, helper):
        return pytree.Serializer(externalizer=helper.externalizer)

    @pytest.fixture
    def unserializer(self, helper):
        return pytree.Unserializer(externalizer=helper.externalizer)

    def test_serialization(self, helper, serializer, convertion_table):
        helper.check_serialization(serializer, convertion_table)

    def test_unserialization(
            self, helper, serializer, unserializer, convertion_table):
        helper.check_unserialization(
            serializer, unserializer, convertion_table)

    def test_freezing(self, helper, serializer, convertion_table):
        helper.check_freezing(serializer, convertion_table)

    def test_symmetry(self, helper, serializer, unserializer):
        helper.check_symmetry(serializer, unserializer)

    @pytest.fixture
    def convertion_table(self, helper):

        def convertion_table(capabilities, freezing):
            # ## Basic immutable types ###

            yield str, [""], str, [""], False
            yield str, ["dummy"], str, ["dummy"], False
            yield unicode, [u""], unicode, [u""], False
            yield unicode, [u"dummy"], unicode, [u"dummy"], False
            yield unicode, [u"áéí"], unicode, [u"áéí"], False
            yield int, [0], int, [0], False
            yield int, [42], int, [42], False
            yield int, [-42], int, [-42], False
            yield long, [long(0)], long, [long(0)], False
            yield long, [2 ** 66], long, [2 ** 66], False
            yield long, [-2 ** 66], long, [-2 ** 66], False
            yield float, [0.0], float, [0.0], False
            yield float, [3.1415926], float, [3.1415926], False
            yield float, [1e24], float, [1e24], False
            yield float, [1e-24], float, [1e-24], False
            yield bool, [True], bool, [True], False
            yield bool, [False], bool, [False], False
            yield type(None), [None], type(None), [None], False

            # ## Types ###
            from datetime import datetime
            yield type, [int], type, [int], False
            yield type, [datetime], type, [datetime], False
            yield (type, [utils.SerializableDummy],
                   type, [utils.SerializableDummy], False)
            yield (InterfaceClass, [DummyInterface],
                   InterfaceClass, [DummyInterface], False)

            # ## Enums ###

            DummyEnum = utils.DummyEnum

            yield DummyEnum, [DummyEnum.a], DummyEnum, [DummyEnum.a], False
            yield DummyEnum, [DummyEnum.c], DummyEnum, [DummyEnum.c], False

            # ## External References ###

            if freezing:
                identifier = (helper.ext_val.type_name, id(helper.ext_val))
                yield (type(helper.ext_val), [helper.ext_val],
                       tuple, [identifier], False)
                yield (type(helper.ext_snap_val), [helper.ext_snap_val],
                       type(id(helper.ext_snap_val)),
                       [id(helper.ext_snap_val)], False)
            else:
                identifier = (helper.ext_val.type_name, id(helper.ext_val))
                yield (utils.SerializableDummy,
                       [helper.ext_val], pytree.External,
                       [pytree.External(identifier)], False)

            # ## Freezing-Only Types ###

            if freezing:
                mod_name = "tests.test_pytree"
                fun_name = mod_name + ".dummy_function"
                meth_name = mod_name + ".DummyClass.dummy_method"

                yield (
                    types.FunctionType, [dummy_function], str, [fun_name],
                    True)

                yield (types.FunctionType, [DummyClass.dummy_method],
                       str, [meth_name], True)

                o = DummyClass()
                yield (
                    types.FunctionType, [o.dummy_method],
                    str, [meth_name], True)

            # ### Basic mutable types plus tuples ###

            # Exception for empty tuple singleton
            yield tuple, [()], tuple, [()], False
            yield tuple, [(1, 2, 3)], tuple, [(1, 2, 3)], True
            yield list, [[]], list, [[]], True
            yield list, [[1, 2, 3]], list, [[1, 2, 3]], True
            yield set, [set([])], set, [set([])], True
            yield set, [set([1, 3])], set, [set([1, 3])], True
            yield dict, [{}], dict, [{}], True
            yield dict, [{1: 2, 3: 4}], dict, [{1: 2, 3: 4}], True

            # Container with different types
            yield (tuple, [(0.1, 2 ** 45, "a", u"z", False, None,
                            (1, ), [2], set([3]), {4: 5})],
                   tuple, [(0.1, 2 ** 45, "a", u"z", False, None,
                            (1, ), [2], set([3]), {4: 5})], True)
            yield (list, [[0.1, 2 ** 45, "a", u"z", False, None,
                           (1, ), [2], set([3]), {4: 5}]],
                   list, [[0.1, 2 ** 45, "a", u"z", False, None,
                           (1, ), [2], set([3]), {4: 5}]], True)
            yield (set, [set([0.1, 2 ** 45, "a", u"z", False, None, (1)])],
                   set, [set([0.1, 2 ** 45, "a", u"z", False, None, (1)])],
                   True)
            yield (dict, [{0.2: 0.1, 2 ** 42: 2 ** 45, "x": "a", u"y": u"z",
                           True: False, None: None, (-1, ): (1, ),
                           8: [2], 9: set([3]), 10: {4: 5}}],
                   dict, [{0.2: 0.1, 2 ** 42: 2 ** 45, "x": "a", u"y": u"z",
                           True: False, None: None, (-1, ): (1, ),
                           8: [2], 9: set([3]), 10: {4: 5}}], True)

            # ## References and Dereferences ###

            Ref = pytree.Reference
            Deref = pytree.Dereference

            # Simple reference in list
            a = []
            b = [a, a]
            yield list, [b], list, [[Ref(1, []), Deref(1)]], True

            # Simple reference in tuple
            a = ()
            b = (a, a)
            yield tuple, [b], tuple, [(Ref(1, ()), Deref(1))], True

            # Simple dereference in dict value.
            a = ()
            b = [a, {1: a}]
            yield list, [b], list, [[Ref(1, ()), {1: Deref(1)}]], True

            # Simple reference in dict value.
            a = ()
            b = [{1: a}, a]
            yield list, [b], list, [[{1: Ref(1, ())}, Deref(1)]], True

            # Simple dereference in dict keys.
            a = ()
            b = [a, {a: 1}]
            yield list, [b], list, [[Ref(1, ()), {Deref(1): 1}]], True

            # Simple reference in dict keys.
            a = ()
            b = [{a: 1}, a]
            yield list, [b], list, [[{Ref(1, ()): 1}, Deref(1)]], True

            # Multiple reference in dictionary values, because dictionary order
            # is not predictable all possibilities have to be tested
            a = {}
            b = {1: a, 2: a, 3: a}
            yield (dict, [b], dict,
                   [{1: Ref(1, {}), 2: Deref(1), 3: Deref(1)},
                    {1: Deref(1), 2: Ref(1, {}), 3: Deref(1)},
                    {1: Deref(1), 2: Deref(1), 3: Ref(1, {})}],
                   True)

            # Multiple reference in dictionary keys, because dictionary order
            # is not predictable all possibilities have to be tested
            a = (1, )
            b = {(1, a): 1, (2, a): 2, (3, a): 3}
            yield (dict, [b], dict,
                   [{(1, Ref(1, (1, ))): 1, (2, Deref(1)): 2, (3, Deref(1)): 3},
                    {(1, Deref(1)): 1, (2, Ref(1, (1, ))): 2, (3, Deref(1)): 3},
                    {(1, Deref(1)): 1, (2, Deref(1)): 2, (3, Ref(1, (1, ))): 3}],
                   True)

            # Simple dereference in set.
            a = ()
            b = [a, set([a])]
            yield list, [b], list, [[Ref(1, ()), set([Deref(1)])]], True

            # Simple reference in set.
            a = ()
            b = [set([a]), a]
            yield list, [b], list, [[set([Ref(1, ())]), Deref(1)]], True

            # Multiple reference in set, because set values order
            # is not predictable all possibilities have to be tested
            a = (1, )
            b = set([(1, a), (2, a), (3, a)])
            yield (set, [b], set,
                   [set([(1, Ref(1, (1, ))), (2, Deref(1)), (3, Deref(1))]),
                    set([(1, Deref(1)), (2, Ref(1, (1, ))), (3, Deref(1))]),
                    set([(1, Deref(1)), (2, Deref(1)), (3, Ref(1, (1, )))])],
                   True)

            # List self-reference
            a = []
            a.append(a)
            yield list, [a], Ref, [Ref(1, [Deref(1)])], True

            # Dict self-reference
            a = {}
            a[1] = a
            yield dict, [a], Ref, [Ref(1, {1: Deref(1)})], True

            # Multiple references
            a = []
            b = [a]
            c = [a, b]
            d = [a, b, c]
            yield (list, [d], list, [[Ref(1, []), Ref(2, [Deref(1)]),
                                      [Deref(1), Deref(2)]]], True)

            # Complex structure without dict or set
            a = ()
            b = (a, )
            b2 = set(b)
            c = (a, b)
            c2 = [c]
            d = (a, b, c)
            d2 = [a, b2, c2]
            e = (b, c, d)
            e2 = [b2, c2, e]
            g = (b, b2, c, c2, d, d2, e, e2)

            yield (tuple, [g], tuple, [(Ref(2, (Ref(1, ()), )),
                                        Ref(4, set([Deref(1)])),
                                        Ref(3, (Deref(1), Deref(2))),
                                        Ref(5, [Deref(3)]),
                                        Ref(6, (Deref(1), Deref(2), Deref(3))),
                                        [Deref(1), Deref(4), Deref(5)],
                                        Ref(7, (Deref(2), Deref(3), Deref(6))),
                                        [Deref(4), Deref(5), Deref(7)])], True)

            Klass = utils.SerializableDummy
            name = reflect.canonical_name(Klass)

            if freezing:
                Inst = lambda v: v
                InstType = dict
            else:
                Inst = lambda v: pytree.Instance(name, v)
                InstType = pytree.Instance

            # Default instance
            o = Klass()
            yield (Klass, [o], InstType,
                   [Inst({"str": "dummy",
                          "unicode": u"dummy",
                          "int": 42,
                          "long": 2 ** 66,
                          "float": 3.1415926,
                          "bool": True,
                          "none": None,
                          "list": [1, 2, 3],
                          "tuple": (1, 2, 3),
                          "set": set([1, 2, 3]),
                          "dict": {1: 2, 3: 4},
                          "ref": None})], True)

            Klass = DummyClass
            name = reflect.canonical_name(Klass)

            if freezing:
                Inst = lambda v: v
                InstType = dict
            else:
                Inst = lambda v: pytree.Instance(name, v)
                InstType = pytree.Instance

            a = Klass()
            b = Klass()
            c = Klass()

            a.ref = b
            b.ref = a
            c.ref = c

            yield (Klass, [a], Ref,
                   [Ref(1, Inst({"ref":
                                 Inst({"ref": Deref(1)})}))], True)

            yield (Klass, [b], Ref,
                   [Ref(1, Inst({"ref":
                                 Inst({"ref": Deref(1)})}))], True)

            yield (Klass, [c], Ref,
                   [Ref(1, Inst({"ref": Deref(1)}))], True)

            yield (list, [[a, b]], list,
                   [[Ref(1, Inst({"ref":
                                  Ref(2, Inst({"ref": Deref(1)}))})),
                     Deref(2)]], True)

            yield (list, [[a, c]], list,
                   [[Ref(1, Inst({"ref":
                                  Inst({"ref": Deref(1)})})),
                     Ref(2, Inst({"ref": Deref(2)}))]], True)

            yield (list, [[a, [a, [a, [a]]]]], list,
                   [[Ref(1, Inst({'ref': Inst({'ref': Deref(1)})})),
                     [Deref(1), [Deref(1), [Deref(1)]]]]], True)

            yield (tuple, [(a, (a, (a, (a, ))))], tuple,
                   [(Ref(1, Inst({'ref': Inst({'ref': Deref(1)})})),
                     (Deref(1), (Deref(1), (Deref(1), ))))], True)

        return convertion_table
