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
from past.types import long
from six import with_metaclass

import itertools
import types

import pytest
from zope.interface import Interface
from zope.interface.declarations import implementer
from zope.interface.interface import InterfaceClass

try:
    from serialization import sexp
    from twisted.spread import jelly
    from twisted.spread.jelly import Jellyable
except ImportError:
    sexp = None
    jelly = None
    Jellyable = object
    skip_msg = (
        '`twisted.spread` needed by this serializer is'
        ' available only for python 2'
    )

import serialization
from serialization import reflect
from serialization.interface import IRestorator, ISerializable, Capabilities

from . import utils


@serialization.register
class DummyClass(serialization.Serializable):

    def dummy_method(self):
        pass


class DummyInterface(Interface):
    pass


def dummy_function():
    pass


class ListSerializableDummy(serialization.Serializable, Jellyable):

    def __init__(self, values):
        self.values = list(values)

    def recover(self, snapshot):
        self.values = list(snapshot)

    def snapshot(self):
        return list(self.values)

    def getStateFor(self, jellyer):
        return self.snapshot()

    def __eq__(self, value):
        return self.values == value.values


@pytest.fixture
def skip_in_sexp_unavailable():
    if None in (sexp, jelly):
        pytest.skip(skip_msg)


@pytest.mark.usefixtures('skip_in_sexp_unavailable')
class TestSExpConverters(object):

    @pytest.fixture
    def serializer(self, helper):
        return sexp.Serializer(externalizer=helper.externalizer)

    @pytest.fixture
    def unserializer(self, helper):
        return sexp.Unserializer(externalizer=helper.externalizer)

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

    def test_jelly_unjelly(self, serializer, helper):
        # jelly do not support meta types, enums and external references.
        caps = set(serializer.converter_capabilities)
        caps -= set([Capabilities.meta_types,
                     Capabilities.new_style_types,
                     Capabilities.external_values,
                     Capabilities.enum_values,
                     Capabilities.enum_keys])
        # strict=False because _Dereference instead real obj, it's jelly issue
        helper._check_symmetry(
            jelly.jelly, jelly.unjelly, capabilities=caps, strict=False)

    def test_unjelly_compatibility(self, serializer, helper):
        # jelly do not support meta types, enums and external references.
        caps = set(serializer.converter_capabilities)
        caps -= set([Capabilities.meta_types,
                     Capabilities.new_style_types,
                     Capabilities.external_values,
                     Capabilities.enum_values,
                     Capabilities.enum_keys])
        # strict=False because _Dereference instead real obj, it's jelly issue
        helper._check_symmetry(
            serializer.convert, jelly.unjelly, capabilities=caps,
            strict=False)

    def test_jelly_compatibility(self, serializer, unserializer, helper):
        # jelly do not support meta types, enums and external references.
        caps = set(serializer.converter_capabilities)
        caps -= set([Capabilities.meta_types,
                     Capabilities.new_style_types,
                     Capabilities.external_values,
                     Capabilities.enum_values,
                     Capabilities.enum_keys])
        helper._check_symmetry(
            jelly.jelly, unserializer.convert, capabilities=caps)

    def test_not_referenceable(self, serializer, helper):
        Klass = utils.NotReferenceableDummy
        name = reflect.canonical_name(Klass)

        obj = Klass()
        data = serializer.convert([obj, obj])

        assert data == [
            "list",
            [name, ["dictionary", ["value", 42]]],
            [name, ["dictionary", ["value", 42]]],
        ]

        data = serializer.freeze([obj, obj])
        assert data == [
            "list",
            ["dictionary", ["value", 42]],
            ["dictionary", ["value", 42]],
        ]

    def test_instances_serialization(self, serializer):
        # Because dictionaries item order is not guaranteed we cannot
        # compare directly directlly the result
        obj = utils.SerializableDummy()
        name = reflect.canonical_name(utils.SerializableDummy)
        data = serializer.convert(obj)
        assert isinstance(data, list)
        assert data[0] == name
        assert isinstance(data[1], list)
        assert data[1][0] == "dictionary"
        dict_vals = data[1][1:]
        assert len(dict_vals) == 12

        assert ['none', ['None']] in dict_vals
        assert ['set', ['set', 1, 2, 3]] in dict_vals
        assert ['str', 'dummy'] in dict_vals
        assert ['tuple', ['tuple', 1, 2, 3]] in dict_vals
        assert ['int', 42] in dict_vals
        assert ['float', 3.1415926] in dict_vals
        assert ['list', ['list', 1, 2, 3]] in dict_vals
        assert ['long', 2 ** 66] in dict_vals
        assert ['bool', ['boolean', 'true']] in dict_vals
        assert ['unicode', ['unicode', 'dummy']] in dict_vals
        assert ['dict', ['dictionary', [1, 2], [3, 4]]] in dict_vals
        assert ['ref', ['None']] in dict_vals

        obj = ListSerializableDummy([1, 2, 3])
        name = reflect.canonical_name(ListSerializableDummy)
        assert serializer.convert(obj) == [name, ['list', 1, 2, 3]]

    @pytest.fixture
    def convertion_table(self, helper):

        def convertion_table(capabilities, freezing):
            ### Basic immutable types ###
            yield str, [""], str, [""], False
            yield str, ["dummy"], str, ["dummy"], False
            yield unicode, [u""], list, [["unicode", ""]], True
            yield unicode, [u"dummy"], list, [["unicode", "dummy"]], True
            yield (unicode, [u"áéí"], list,
                   [["unicode", '\xc3\xa1\xc3\xa9\xc3\xad']], True)
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
            yield bool, [True], list, [["boolean", "true"]], True
            yield bool, [False], list, [["boolean", "false"]], True
            yield types.NoneType, [None], list, [["None"]], True

            ### Types ###
            from datetime import datetime
            yield type, [int], list, [["class", "__builtin__.int"]], False
            yield (
                type, [datetime], list,
                [["class", "datetime.datetime"]], False)
            name = reflect.canonical_name(
                utils.SerializableDummy)
            yield (type, [utils.SerializableDummy],
                   list, [["class", name]], False)
            name = reflect.canonical_name(DummyInterface)
            yield (InterfaceClass, [DummyInterface],
                   list, [["class", name]], False)

            ### Enums ###

            DummyEnum = utils.DummyEnum
            name = reflect.canonical_name(DummyEnum)

            if Capabilities.enum_values in Capabilities:
                yield (DummyEnum, [DummyEnum.a],
                       list, [["enum", name, DummyEnum.a.name]], False)
                yield (DummyEnum, [DummyEnum.c],
                       list, [["enum", name, DummyEnum.c.name]], False)

            ### External References ###

            if freezing:
                identifier = [
                    "tuple", helper.ext_val.type_name, id(helper.ext_val)]
                yield (type(helper.ext_val), [helper.ext_val],
                       list, [identifier], False)
                yield (type(helper.ext_snap_val), [helper.ext_snap_val],
                       int, [id(helper.ext_snap_val)], False)
            else:
                identifier = [
                    "tuple", helper.ext_val.type_name, id(helper.ext_val)]
                yield (utils.SerializableDummy,
                       [helper.ext_val], list,
                        [["external", identifier]], False)

            ### Freezing-Only Types ###

            if freezing:
                mod_name = "tests.test_sexp"
                fun_name = mod_name + ".dummy_function"
                meth_name = mod_name + ".DummyClass.dummy_method"

                yield (
                    types.FunctionType, [dummy_function],
                    str, [fun_name], True)

                yield (types.FunctionType, [DummyClass.dummy_method],
                       str, [meth_name], True)

                o = DummyClass()
                yield (
                    types.FunctionType, [o.dummy_method], str,
                     [meth_name], True)

            ### Basic containers ###
            # Exception for empty tuple
            yield tuple, [()], list, [["tuple"]], False
            yield tuple, [(1, 2, 3)], list, [["tuple", 1, 2, 3]], True
            yield list, [[]], list, [["list"]], True
            yield list, [[1, 2, 3]], list, [["list", 1, 2, 3]], True
            yield set, [set([])], list, [["set"]], True
            yield set, [set([1, 3])], list, [["set", 1, 3]], True
            yield dict, [{}], list, [["dictionary"]], True
            yield (dict, [{1: 2, 3: 4}], list,
                   [["dictionary", [1, 2], [3, 4]]], True)

            # Tuple with various value type
            yield (tuple, [(0.1, 2 ** 45, "a", u"z", False, None,
                            (1, ), [2], set([3]), {4: 5})],
                   list, [["tuple", 0.1, 2 ** 45, "a", ["unicode", "z"],
                           ["boolean", "false"], ["None"], ["tuple", 1],
                           ["list", 2], ["set", 3], ["dictionary", [4, 5]]]],
                           True)
            # List with various value type
            yield (list, [[0.1, 2 ** 45, "a", u"z", False, None,
                           (1, ), [2], set([3]), {4: 5}]],
                   list, [["list", 0.1, 2 ** 45, "a", ["unicode", "z"],
                           ["boolean", "false"], ["None"], ["tuple", 1],
                           ["list", 2], ["set", 3], ["dictionary", [4, 5]]]],
                           True)
            # Set with various value type
            # Because set are not ordered every order is possible
            values = [0.1, 2 ** 45, "a", ["unicode", "z"],
                      ["boolean", "false"], ["None"], ["tuple", 1]]
            expected = [["set"] + values]
            alternatives = [["set"] + list(perm)
                            for perm in itertools.permutations(values)]
            yield (set, [set([0.1, 2 ** 45, "a", u"z", False, None, (1, )])],
                    [], list, expected, alternatives, True)
            # Dictionary with various value type
            # Because dictionaries are not ordered every order is possible
            values = [[1, 0.1], [2, 2 ** 45], [3, "a"], [4, ["unicode", "z"]],
                      [5, ["boolean", "false"]]]
            expected = [["dictionary"] + values]
            alternatives = [["dictionary"] + list(perm)
                            for perm in itertools.permutations(values)]
            yield (dict, [{1: 0.1, 2: 2 ** 45, 3: "a", 4: u"z", 5: False}], [],
                   list, expected, alternatives, True)

            values = [[6, ["None"]], [7, ["tuple", 1]], [8, ["list", 2]],
                      [9, ["set", 3]], [0, ["dictionary", [4, 5]]]]
            expected = [["dictionary"] + values]
            alternatives = [["dictionary"] + list(perm)
                            for perm in itertools.permutations(values)]
            yield (dict, [{6: None, 7: (1, ), 8: [2], 9: set([3]), 0: {4: 5}}],
                    [], list, expected, alternatives, True)

            values = [[0.1, 1], [2 ** 45, 2], ["a", 3], [["unicode", "z"], 4],
                      [["boolean", "false"], 5], [["None"], 6],
                      [["tuple", 1], 7]]
            expected = [["dictionary"] + values]
            alternatives = [["dictionary"] + list(perm)
                            for perm in itertools.permutations(values)]
            yield (dict, [{0.1: 1, 2 ** 45: 2, "a": 3, u"z": 4,
                           False: 5, None: 6, (1, ): 7}], [],
                   list, expected, alternatives, True)

            ### References and Dereferences ###

            Ref = lambda refid, value: ["reference", refid, value]
            Deref = lambda refid: ["dereference", refid]

            # Simple reference in list
            a = []
            b = [a, a]
            yield list, [b], list, [["list", Ref(1, ["list"]), Deref(1)]], True

            # Simple reference in tuple
            a = ()
            b = (a, a)
            yield (
                tuple, [b], list,
                [["tuple", Ref(1, ["tuple"]), Deref(1)]], True)

            # Simple dereference in dict value.
            a = {}
            b = [a, {1: a}]
            yield (list, [b], list, [["list", Ref(1, ["dictionary"]),
                                      ["dictionary", [1, Deref(1)]]]], True)

            # Simple reference in dict value.
            a = set([])
            b = [{1: a}, a]
            yield (list, [b], list, [["list",
                                      ["dictionary", [1, Ref(1, ["set"])]],
                                      Deref(1)]], True)

            # Simple dereference in dict keys.
            a = ()
            b = [a, {a: 1}]
            yield (list, [b], list, [["list", Ref(1, ["tuple"]),
                                      ["dictionary", [Deref(1), 1]]]], True)

            # Simple reference in dict keys.
            a = (1, 2)
            b = [{a: 1}, a]
            yield (list, [b], list,
                   [["list", ["dictionary", [Ref(1, ["tuple", 1, 2]), 1]],
                    Deref(1)]], True)

            # Multiple reference in dictionary values, because dictionary order
            # is not predictable all possibilities have to be tested
            a = set()
            b = {1: a, 2: a, 3: a}

            values1 = [[1, Ref(1, ["set"])], [2, Deref(1)], [3, Deref(1)]]
            values2 = [[2, Ref(1, ["set"])], [3, Deref(1)], [1, Deref(1)]]
            values3 = [[3, Ref(1, ["set"])], [1, Deref(1)], [2, Deref(1)]]
            expected1 = [["dictionary"] + values1]
            expected2 = [["dictionary"] + values2]
            expected3 = [["dictionary"] + values3]
            alternatives1 = [["dictionary"] + list(perm)
                             for perm in itertools.permutations(values1)]
            alternatives2 = [["dictionary"] + list(perm)
                             for perm in itertools.permutations(values2)]
            alternatives3 = [["dictionary"] + list(perm)
                             for perm in itertools.permutations(values3)]

            yield (dict, [b], [], list, expected1 + expected2 + expected3,
                   alternatives1 + alternatives2 + alternatives3, True)

            # Multiple reference in dictionary keys, because dictionary order
            # is not predictable all possibilities have to be tested
            a = (1, )
            b = {(1, a): 1, (2, a): 2, (3, a): 3}

            values1 = [
                [["tuple", 1, Ref(1, ["tuple", 1])], 1],
                [["tuple", 2, Deref(1)], 2], [["tuple", 3, Deref(1)], 3]]
            values2 = [
                [["tuple", 2, Ref(1, ["tuple", 1])], 2],
                [["tuple", 3, Deref(1)], 3], [["tuple", 1, Deref(1)], 1]]
            values3 = [
                [["tuple", 3, Ref(1, ["tuple", 1])], 3],
                [["tuple", 1, Deref(1)], 1], [["tuple", 2, Deref(1)], 2]]
            expected1 = [["dictionary"] + values1]
            expected2 = [["dictionary"] + values2]
            expected3 = [["dictionary"] + values3]
            alternatives1 = [["dictionary"] + list(perm)
                             for perm in itertools.permutations(values1)]
            alternatives2 = [["dictionary"] + list(perm)
                             for perm in itertools.permutations(values2)]
            alternatives3 = [["dictionary"] + list(perm)
                             for perm in itertools.permutations(values3)]

            yield (dict, [b], [], list, expected1 + expected2 + expected3,
                   alternatives1 + alternatives2 + alternatives3, True)

            # Simple dereference in set.
            a = ("a", )
            b = [a, set([a])]
            yield (list, [b], list, [["list", Ref(1, ["tuple", "a"]),
                                      ["set", Deref(1)]]], True)

            # Simple reference in set.
            a = ("b", )
            b = [set([a]), a]
            yield (list, [b], list, [["list", ["set", Ref(1, ["tuple", "b"])],
                                      Deref(1)]], True)

            # Multiple reference in set, because set values order
            # is not predictable all possibilities have to be tested
            a = (1, )
            b = set([(1, a), (2, a), (3, a)])

            values1 = [["tuple", 1, Ref(1, ["tuple", 1])],
                       ["tuple", 2, Deref(1)], ["tuple", 3, Deref(1)]]
            values2 = [["tuple", 2, Ref(1, ["tuple", 1])],
                       ["tuple", 3, Deref(1)], ["tuple", 1, Deref(1)]]
            values3 = [["tuple", 3, Ref(1, ["tuple", 1])],
                       ["tuple", 1, Deref(1)], ["tuple", 2, Deref(1)]]
            expected1 = [["set"] + values1]
            expected2 = [["set"] + values2]
            expected3 = [["set"] + values3]
            alternatives1 = [["set"] + list(perm)
                             for perm in itertools.permutations(values1)]
            alternatives2 = [["set"] + list(perm)
                             for perm in itertools.permutations(values2)]
            alternatives3 = [["set"] + list(perm)
                             for perm in itertools.permutations(values3)]

            yield (set, [b], [], list, expected1 + expected2 + expected3,
                   alternatives1 + alternatives2 + alternatives3, True)

            # List self-reference
            a = []
            a.append(a)
            yield list, [a], list, [Ref(1, ["list", Deref(1)])], True

            # Dict self-reference
            a = {}
            a[1] = a
            yield (
                dict, [a], list,
                [Ref(1, ["dictionary", [1, Deref(1)]])], True)

            # Multiple references
            a = []
            b = [a]
            c = [a, b]
            d = [a, b, c]
            yield (list, [d], list, [["list", Ref(1, ["list"]),
                                      Ref(2, ["list", Deref(1)]),
                                      ["list", Deref(1), Deref(2)]]], True)

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

            yield (tuple, [g], list,
                   [['tuple', Ref(2, ['tuple', Ref(1, ['tuple'])]),
                     Ref(4, ['set', Deref(1)]),
                     Ref(3, ['tuple', Deref(1), Deref(2)]),
                     Ref(5, ['list', Deref(3)]),
                     Ref(6, ['tuple', Deref(1), Deref(2), Deref(3)]),
                     ['list', Deref(1), Deref(4), Deref(5)],
                     Ref(7, ['tuple', Deref(2), Deref(3), Deref(6)]),
                     ['list', Deref(4), Deref(5), Deref(7)]]], True)

            Klass = utils.SerializableDummy

            # Object instances
            o = Klass()
            # Update the instance to have only one attribute
            del o.set
            del o.dict
            del o.str
            del o.unicode
            del o.long
            del o.float
            del o.bool
            del o.none
            del o.list
            del o.tuple
            del o.ref
            o.int = 101

            if freezing:
                yield (Klass, [o], list,
                       [["dictionary", ["int", 101]]], True)
            else:
                yield (Klass, [o], list,
                       [[reflect.canonical_name(Klass),
                         ["dictionary", ["int", 101]]]], True)

            Klass = DummyClass
            name = reflect.canonical_name(Klass)
            if freezing:
                Inst = lambda v: v
            else:
                Inst = lambda v: [name, v]

            a = Klass()
            b = Klass()
            c = Klass()

            a.ref = b
            b.ref = a
            c.ref = c

            yield (Klass, [a], list,
                   [Ref(1, Inst(
                       ["dictionary",
                        ["ref", Inst(["dictionary", ["ref", Deref(1)]])]]))],
                         True)

            yield (Klass, [b], list,
                   [Ref(1, Inst(
                       ["dictionary",
                        ["ref", Inst(["dictionary", ["ref", Deref(1)]])]]))],
                        True)

            yield (Klass, [c], list,
                   [Ref(1, Inst(["dictionary", ["ref", Deref(1)]]))], True)

            yield (list, [[a, b]], list,
                   [["list", Ref(1, Inst(
                       ["dictionary", ["ref",
                                       Ref(2, Inst(["dictionary",
                                                    ["ref", Deref(1)]]))]])),
                     Deref(2)]], True)

            yield (list, [[a, c]], list,
                   [["list", Ref(1, Inst(
                       ["dictionary", ["ref",
                                       Inst(["dictionary",
                                             ["ref", Deref(1)]])]])),
                     Ref(2, Inst(["dictionary", ["ref", Deref(2)]]))]], True)

        return convertion_table


@implementer(IRestorator)
class MetaTest(type):
    pass


@implementer(ISerializable)
class Test(with_metaclass(MetaTest, object)):

    recover_count = 0
    restored_count = 0
    snapshot = None

    @classmethod
    def reset(cls):
        cls.recover_count = 0
        cls.restored_count = 0

    @classmethod
    def prepare(cls):
        return cls.__new__(cls)

    @classmethod
    def restore(cls, snapshot):
        return cls.prepare()

    def recover(self, snapshot):
        cls = type(self)
        cls.recover_count = getattr(cls, "recover_count", 0) + 1
        self.snapshot = snapshot

    def restored(self):
        cls = type(self)
        cls.restored_count = getattr(cls, "restored_count", 0) + 1

    def __repr__(self):
        return "<%s #%d: %r>" % (type(self).__name__, id(self), self.snapshot)


@serialization.register
class A(Test):
    type_name = "A"


@serialization.register
class B(Test):
    type_name = "B"


@serialization.register
class C(Test):
    type_name = "C"


@serialization.register
class D(Test):
    type_name = "D"


@serialization.register
class E(Test):
    type_name = "E"


@serialization.register
class F(Test):
    type_name = "F"


data1 = ['list',
         ['reference', 1,
          ['A', ['list',
                 ['B', 0],
                 ['C', [
                     'list',
                     ['reference', 4, ['D',
                                       ['list',
                                        ['dereference', 1],
                                        ['C', ['reference', 2, ['B', 0]]]]]],
                     ['E', ['C', 0]],
                     ['dereference', 2],
                     ['reference', 3, ['B', 0]]]]]]],
         ['C', 0],
         ['C', ['F', 0]],
         ['C', ['list',
                ['F', 0],
                ['dereference', 3]]],
         ['dereference', 4]]


data2 = ['list',
         ['list',
          ['A', 0],
          ['dereference', 1],
          ['reference', 2, ['C', 0]],
          ['D', 0]],
         ['list',
          ['A', 0],
          ['reference', 1, ['B', 0]],
          ['dereference', 2],
          ['D', 0]]]


@pytest.mark.usefixtures('skip_in_sexp_unavailable')
class TestInstanceCreation(object):

    @pytest.fixture(autouse=True)
    def reset_all(self, request):

        def reset_all():
            for cls in (A, B, C, D, E, F):
                cls.reset()

        request.addfinalizer(reset_all)

    def test_complex_use_case(self):
        """This data structure is base on a real feat snapshot.
           This test was added to fix and keep fixed an unserialization
           bug causing additional instances beeing created and there
           restored method being called.
           """
        unserializer = sexp.Unserializer()
        unserializer.convert(data1)

        assert A.recover_count == 1
        assert A.restored_count == 1
        assert B.recover_count == 3
        assert B.restored_count == 3
        assert C.recover_count == 6
        assert C.restored_count == 6
        assert D.recover_count == 1
        assert D.restored_count == 1
        assert E.recover_count == 1
        assert E.restored_count == 1
        assert F.recover_count == 2
        assert F.restored_count == 2

    def test_cross_references(self):
        unserializer = sexp.Unserializer()
        unserializer.convert(data2)

        assert A.recover_count == 2
        assert A.restored_count == 2
        assert B.recover_count == 1
        assert B.restored_count == 1
        assert C.recover_count == 1
        assert C.restored_count == 1
        assert D.recover_count == 2
        assert D.restored_count == 2
