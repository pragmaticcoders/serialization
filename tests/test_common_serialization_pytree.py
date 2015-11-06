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

import types

from zope.interface import Interface
from zope.interface.interface import InterfaceClass

from feat.common import serialization, reflect
from feat.common.serialization import pytree, base
from feat.interface.serialization import *

from . import common, common_serialization


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


class Versioned(serialization.Serializable, base.VersionAdapter):

    __metaclass__ = type("MetaAv1", (type(serialization.Serializable),
                                     type(base.VersionAdapter)), {})


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


class PyTreeVersionTest(common.TestCase):

    def adapt(self, value, registry, source_ver, inter_ver, target_ver):
        serializer = pytree.Serializer(source_ver=source_ver,
                                       target_ver=inter_ver)
        data = serializer.convert(value)
        unserializer = pytree.Unserializer(registry=registry,
                                           source_ver=inter_ver,
                                           target_ver=target_ver)
        return unserializer.convert(data)

    def testSimpleUpgrades(self):
        r1 = serialization.Registry()
        r1.register(Av1)
        r2 = serialization.Registry()
        r2.register(Av2)
        r3 = serialization.Registry()
        r3.register(Av3)

        a1 = Av1()
        self.assertTrue(hasattr(a1, "foo"))
        self.assertFalse(hasattr(a1, "bar"))
        self.assertEqual(a1.foo, "42")
        a1.foo = "18"

        a12 = self.adapt(a1, r2, 1, 1, 2)
        self.assertTrue(hasattr(a12, "foo"))
        self.assertFalse(hasattr(a12, "bar"))
        self.assertEqual(a12.foo, 18)

        a13 = self.adapt(a1, r3, 1, 1, 3)
        self.assertFalse(hasattr(a13, "foo"))
        self.assertTrue(hasattr(a13, "bar"))
        self.assertEqual(a13.bar, 18)

        a2 = Av2()
        self.assertTrue(hasattr(a2, "foo"))
        self.assertFalse(hasattr(a2, "bar"))
        self.assertEqual(a2.foo, 42)
        a2.foo = 23

        a23 = self.adapt(a2, r3, 2, 2, 3)
        self.assertFalse(hasattr(a23, "foo"))
        self.assertTrue(hasattr(a23, "bar"))
        self.assertEqual(a23.bar, 23)

    def testSimpleDowngrade(self):
        r1 = serialization.Registry()
        r1.register(Av1)
        r2 = serialization.Registry()
        r2.register(Av2)
        r3 = serialization.Registry()
        r3.register(Av3)

        a3 = Av3()
        self.assertFalse(hasattr(a3, "foo"))
        self.assertTrue(hasattr(a3, "bar"))
        self.assertEqual(a3.bar, 42)
        a3.bar = 24

        a32 = self.adapt(a3, r2, 3, 2, 2)
        self.assertTrue(hasattr(a32, "foo"))
        self.assertFalse(hasattr(a32, "bar"))
        self.assertEqual(a32.foo, 24)

        a31 = self.adapt(a3, r2, 3, 2, 1)
        self.assertTrue(hasattr(a31, "foo"))
        self.assertFalse(hasattr(a31, "bar"))
        self.assertEqual(a31.foo, "24")

        a31 = self.adapt(a3, r1, 3, 1, 1)
        self.assertTrue(hasattr(a31, "foo"))
        self.assertFalse(hasattr(a31, "bar"))
        self.assertEqual(a31.foo, "24")

        a2 = Av2()
        self.assertTrue(hasattr(a2, "foo"))
        self.assertFalse(hasattr(a2, "bar"))
        self.assertEqual(a2.foo, 42)
        a2.foo = 18

        a21 = self.adapt(a2, r1, 2, 1, 1)
        self.assertTrue(hasattr(a21, "foo"))
        self.assertFalse(hasattr(a21, "bar"))
        self.assertEqual(a21.foo, "18")

    def testSimpleDownUp(self):
        r1 = serialization.Registry()
        r1.register(Av1)
        r2 = serialization.Registry()
        r2.register(Av2)
        r3 = serialization.Registry()
        r3.register(Av3)

        a2 = Av2()
        self.assertTrue(hasattr(a2, "foo"))
        self.assertFalse(hasattr(a2, "bar"))
        self.assertEqual(a2.foo, 42)
        a2.foo = 18

        a23 = self.adapt(a2, r3, 2, 1, 3)
        self.assertFalse(hasattr(a23, "foo"))
        self.assertTrue(hasattr(a23, "bar"))
        self.assertEqual(a23.bar, 18)

    def testCompoundUpgrades(self):
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
        self.assertTrue(hasattr(b1, "a"))
        self.assertTrue(hasattr(b1, "b"))
        self.assertTrue(hasattr(b1, "c"))
        self.assertFalse(hasattr(b1, "values"))
        self.assertEqual(b1.a.foo, "1")
        self.assertEqual(b1.b.foo, "2")
        self.assertEqual(b1.c.foo, "3")
        b1.a.foo = "4"
        b1.b.foo = "5"
        b1.c.foo = "6"

        b12 = self.adapt(b1, r2, 1, 1, 2)
        self.assertFalse(hasattr(b12, "a"))
        self.assertFalse(hasattr(b12, "b"))
        self.assertFalse(hasattr(b12, "c"))
        self.assertTrue(hasattr(b12, "values"))
        self.assertTrue(isinstance(b12.values, list))
        self.assertEqual(b12.values[0].foo, 4)
        self.assertEqual(b12.values[1].foo, 5)
        self.assertEqual(b12.values[2].foo, 6)

        b13 = self.adapt(b1, r3, 1, 1, 3)
        self.assertFalse(hasattr(b13, "a"))
        self.assertFalse(hasattr(b13, "b"))
        self.assertFalse(hasattr(b13, "c"))
        self.assertTrue(hasattr(b13, "values"))
        self.assertTrue(isinstance(b13.values, dict))
        self.assertEqual(b13.values["a"].bar, 4)
        self.assertEqual(b13.values["b"].bar, 5)
        self.assertEqual(b13.values["c"].bar, 6)

        b2 = Bv2()
        self.assertFalse(hasattr(b2, "a"))
        self.assertFalse(hasattr(b2, "b"))
        self.assertFalse(hasattr(b2, "c"))
        self.assertTrue(hasattr(b2, "values"))
        self.assertTrue(isinstance(b2.values, list))
        self.assertEqual(b2.values[0].foo, 1)
        self.assertEqual(b2.values[1].foo, 2)
        self.assertEqual(b2.values[2].foo, 3)
        b2.values[0].foo = 4
        b2.values[1].foo = 5
        b2.values[2].foo = 6

        b23 = self.adapt(b2, r3, 2, 2, 3)
        self.assertFalse(hasattr(b23, "a"))
        self.assertFalse(hasattr(b23, "b"))
        self.assertFalse(hasattr(b23, "c"))
        self.assertTrue(hasattr(b23, "values"))
        self.assertTrue(isinstance(b23.values, dict))
        self.assertEqual(b23.values["a"].bar, 4)
        self.assertEqual(b23.values["b"].bar, 5)
        self.assertEqual(b23.values["c"].bar, 6)

    def testCompoundDowngrade(self):
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
        self.assertFalse(hasattr(b3, "a"))
        self.assertFalse(hasattr(b3, "b"))
        self.assertFalse(hasattr(b3, "c"))
        self.assertTrue(hasattr(b3, "values"))
        self.assertTrue(isinstance(b3.values, dict))
        self.assertEqual(b3.values["a"].bar, 1)
        self.assertEqual(b3.values["b"].bar, 2)
        self.assertEqual(b3.values["c"].bar, 3)
        b3.values["a"].bar = 4
        b3.values["b"].bar = 5
        b3.values["c"].bar = 6

        b32 = self.adapt(b3, r2, 3, 2, 2)
        self.assertFalse(hasattr(b32, "a"))
        self.assertFalse(hasattr(b32, "b"))
        self.assertFalse(hasattr(b32, "c"))
        self.assertTrue(hasattr(b32, "values"))
        self.assertTrue(isinstance(b32.values, list))
        self.assertEqual(b32.values[0].foo, 4)
        self.assertEqual(b32.values[1].foo, 5)
        self.assertEqual(b32.values[2].foo, 6)

        b32 = self.adapt(b3, r3, 3, 3, 2)
        self.assertFalse(hasattr(b32, "a"))
        self.assertFalse(hasattr(b32, "b"))
        self.assertFalse(hasattr(b32, "c"))
        self.assertTrue(hasattr(b32, "values"))
        self.assertTrue(isinstance(b32.values, list))
        self.assertEqual(b32.values[0].foo, 4)
        self.assertEqual(b32.values[1].foo, 5)
        self.assertEqual(b32.values[2].foo, 6)

        b31 = self.adapt(b3, r1, 3, 1, 1)
        self.assertTrue(hasattr(b31, "a"))
        self.assertTrue(hasattr(b31, "b"))
        self.assertTrue(hasattr(b31, "c"))
        self.assertFalse(hasattr(b31, "values"))
        self.assertEqual(b31.a.foo, "4")
        self.assertEqual(b31.b.foo, "5")
        self.assertEqual(b31.c.foo, "6")

        b31 = self.adapt(b3, r2, 3, 2, 1)
        self.assertTrue(hasattr(b31, "a"))
        self.assertTrue(hasattr(b31, "b"))
        self.assertTrue(hasattr(b31, "c"))
        self.assertFalse(hasattr(b31, "values"))
        self.assertEqual(b31.a.foo, "4")
        self.assertEqual(b31.b.foo, "5")
        self.assertEqual(b31.c.foo, "6")

        b2 = Bv2()
        self.assertFalse(hasattr(b2, "a"))
        self.assertFalse(hasattr(b2, "b"))
        self.assertFalse(hasattr(b2, "c"))
        self.assertTrue(hasattr(b2, "values"))
        self.assertTrue(isinstance(b2.values, list))
        self.assertEqual(b2.values[0].foo, 1)
        self.assertEqual(b2.values[1].foo, 2)
        self.assertEqual(b2.values[2].foo, 3)
        b2.values[0].foo = 4
        b2.values[1].foo = 5
        b2.values[2].foo = 6

        b21 = self.adapt(b2, r1, 2, 1, 1)
        self.assertTrue(hasattr(b21, "a"))
        self.assertTrue(hasattr(b21, "b"))
        self.assertTrue(hasattr(b21, "c"))
        self.assertFalse(hasattr(b21, "values"))
        self.assertEqual(b21.a.foo, "4")
        self.assertEqual(b21.b.foo, "5")
        self.assertEqual(b21.c.foo, "6")


class GenericSerializationTest(common.TestCase):

    def setUp(self):
        common.TestCase.setUp(self)
        self.serializer = pytree.Serializer()
        self.unserializer = pytree.Unserializer()

    def testRestoredCall(self):
        orig = DummySerializable(42)
        obj = self.unserializer.convert(self.serializer.convert(orig))
        self.assertEqual(type(orig), type(obj))
        self.assertEqual(orig.value, obj.value)
        self.assertTrue(obj._restored)

        orig = DummyImmutableSerializable(42)
        obj = self.unserializer.convert(self.serializer.convert(orig))
        self.assertEqual(type(orig), type(obj))
        self.assertEqual(orig.value, obj.value)
        self.assertTrue(obj._restored)

    def testFreezingTags(self):
        instance = DummyClass()
        frozen = self.serializer.freeze(instance.dummer_method)
        self.assertEqual('dummy_tag', frozen)

    def testNotReferenceable(self):
        Klass = common_serialization.NotReferenceableDummy
        Inst = pytree.Instance
        name = reflect.canonical_name(Klass)

        obj = Klass()
        data = self.serializer.convert([obj, obj])

        self.assertEqual(data, [Inst(name, {"value": 42}),
                                Inst(name, {"value": 42})])

        data = self.serializer.freeze([obj, obj])

        self.assertEqual(data, [{"value": 42}, {"value": 42}])


class PyTreeConvertersTest(common_serialization.ConverterTest):

    def setUp(self):
        common_serialization.ConverterTest.setUp(self)
        ext = self.externalizer
        self.serializer = pytree.Serializer(externalizer = ext)
        self.unserializer = pytree.Unserializer(externalizer = ext)

    def convertion_table(self, capabilities, freezing):
        ### Basic immutable types ###

        yield str, [""], str, [""], False
        yield str, ["dummy"], str, ["dummy"], False
        yield unicode, [u""], unicode, [u""], False
        yield unicode, [u"dummy"], unicode, [u"dummy"], False
        yield unicode, [u"áéí"], unicode, [u"áéí"], False
        yield int, [0], int, [0], False
        yield int, [42], int, [42], False
        yield int, [-42], int, [-42], False
        yield long, [0L], long, [0L], False
        yield long, [2**66], long, [2**66], False
        yield long, [-2**66], long, [-2**66], False
        yield float, [0.0], float, [0.0], False
        yield float, [3.1415926], float, [3.1415926], False
        yield float, [1e24], float, [1e24], False
        yield float, [1e-24], float, [1e-24], False
        yield bool, [True], bool, [True], False
        yield bool, [False], bool, [False], False
        yield type(None), [None], type(None), [None], False

        ### Types ###
        from datetime import datetime
        yield type, [int], type, [int], False
        yield type, [datetime], type, [datetime], False
        yield (type, [common_serialization.SerializableDummy],
               type, [common_serialization.SerializableDummy], False)
        yield (InterfaceClass, [DummyInterface],
               InterfaceClass, [DummyInterface], False)

        ### Enums ###

        DummyEnum = common_serialization.DummyEnum

        yield DummyEnum, [DummyEnum.a], DummyEnum, [DummyEnum.a], False
        yield DummyEnum, [DummyEnum.c], DummyEnum, [DummyEnum.c], False

        ### External References ###

        if freezing:
            identifier = (self.ext_val.type_name, id(self.ext_val))
            yield (type(self.ext_val), [self.ext_val],
                   tuple, [identifier], False)
            yield (type(self.ext_snap_val), [self.ext_snap_val],
                   type(id(self.ext_snap_val)), [id(self.ext_snap_val)], False)
        else:
            identifier = (self.ext_val.type_name, id(self.ext_val))
            yield (common_serialization.SerializableDummy, [self.ext_val],
                   pytree.External, [pytree.External(identifier)], False)

        ### Freezing-Only Types ###

        if freezing:
            mod_name = "feat.test.test_common_serialization_pytree"
            fun_name = mod_name + ".dummy_function"
            meth_name = mod_name + ".DummyClass.dummy_method"

            yield types.FunctionType, [dummy_function], str, [fun_name], True

            yield (types.FunctionType, [DummyClass.dummy_method],
                   str, [meth_name], True)

            o = DummyClass()
            yield types.FunctionType, [o.dummy_method], str, [meth_name], True

        #### Basic mutable types plus tuples ###

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
        yield (tuple, [(0.1, 2**45, "a", u"z", False, None,
                        (1, ), [2], set([3]), {4: 5})],
               tuple, [(0.1, 2**45, "a", u"z", False, None,
                        (1, ), [2], set([3]), {4: 5})], True)
        yield (list, [[0.1, 2**45, "a", u"z", False, None,
                       (1, ), [2], set([3]), {4: 5}]],
               list, [[0.1, 2**45, "a", u"z", False, None,
                       (1, ), [2], set([3]), {4: 5}]], True)
        yield (set, [set([0.1, 2**45, "a", u"z", False, None, (1)])],
               set, [set([0.1, 2**45, "a", u"z", False, None, (1)])], True)
        yield (dict, [{0.2: 0.1, 2**42: 2**45, "x": "a", u"y": u"z",
                       True: False, None: None, (-1, ): (1, ),
                       8: [2], 9: set([3]), 10: {4: 5}}],
               dict, [{0.2: 0.1, 2**42: 2**45, "x": "a", u"y": u"z",
                       True: False, None: None, (-1, ): (1, ),
                       8: [2], 9: set([3]), 10: {4: 5}}], True)

        ### References and Dereferences ###

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

        Klass = common_serialization.SerializableDummy
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
                      "long": 2**66,
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
                    Ref(2, Inst({"ref": Deref(1)}))})), Deref(2)]], True)

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
