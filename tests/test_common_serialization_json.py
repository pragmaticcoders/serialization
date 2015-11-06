# Headers in this file shall remain intact.
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

import itertools
import types

from zope.interface import Interface
from zope.interface.interface import InterfaceClass

from feat.common import reflect, serialization, formatable
from feat.common.serialization import base, json
from feat.interface.serialization import *
from feat.test import common


from . import common_serialization


@serialization.register
class DummyClass(serialization.Serializable):

    def dummy_method(self):
        pass


def dummy_function():
    pass


class DummyInterface(Interface):
    pass


class JSONConvertersTest(common_serialization.ConverterTest):

    def setUp(self):
        common_serialization.ConverterTest.setUp(self)
        ext = self.externalizer
        self.serializer = json.Serializer(externalizer=ext)
        self.unserializer = json.Unserializer(externalizer=ext)

    def convertion_table(self, capabilities, freezing):
        ### Basic immutable types ###

        yield str, [""], str, ['[".enc", "UTF8", ""]',
                               '[".bytes", ""]'], False
        yield str, ["dummy"], str, ['[".enc", "UTF8", "dummy"]',
                                    '[".bytes", "ZHVtbXk="]'], False
        yield str, ["\xFF"], str, ['[".bytes", "/w=="]'], False
        yield unicode, [u""], str, ['""'], False
        yield unicode, [u"dummy"], str, ['"dummy"'], False
        yield unicode, [u"áéí"], str, ['"\\u00e1\\u00e9\\u00ed"'], False
        yield [int, long], [0], str, ["0"], False
        yield [int, long], [42], str, ["42"], False
        yield [int, long], [-42], str, ["-42"], False
        yield [int, long], [0L], str, ["0"], False
        yield long, [2**72], str, ["4722366482869645213696"], False
        yield long, [-2**72], str, ["-4722366482869645213696"], False
        yield float, [0.0], str, ["0.0"], False
        yield float, [3.141], str, ["3.141"], False
        yield float, [-3.141], str, ["-3.141"], False
        yield float, [1e20], str, ["1e+20"], False
        yield float, [1e-22], str, ["1e-22"], False
        yield bool, [True], str, ["true"], False
        yield bool, [False], str, ["false"], False
        yield type(None), [None], str, ["null"], False

        ### Types ###
        from datetime import datetime
        yield type, [int], str, ['[".type", "__builtin__.int"]'], False
        yield (type, [datetime],
               str, ['[".type", "datetime.datetime"]'], False)
        yield (type, [common_serialization.SerializableDummy],
               str, ['[".type", "feat.test.common_serialization.'
                     'SerializableDummy"]'], False)
        yield (InterfaceClass, [DummyInterface],
               str, ['[".type", "feat.test.test_common_serialization_json.'
                     'DummyInterface"]'], False)

        ### Enums ###

        DummyEnum = common_serialization.DummyEnum

        yield (DummyEnum, [DummyEnum.a],
               str, ['[".enum", "feat.test.common_serialization.'
                     'DummyEnum.a"]'], False)
        yield (DummyEnum, [DummyEnum.c],
               str, ['[".enum", "feat.test.common_serialization.'
                     'DummyEnum.c"]'], False)

        ### External References ###

        if freezing:
            name = '[".enc", "UTF8", "%s"]' % self.ext_val.type_name
            identifier = '[".tuple", %s, %d]' % (name, id(self.ext_val))
            yield (type(self.ext_val), [self.ext_val],
                   str, [identifier], False)
            yield (type(self.ext_snap_val), [self.ext_snap_val],
                   str, [str(id(self.ext_snap_val))], False)
        else:
            name = '[".enc", "UTF8", "%s"]' % self.ext_val.type_name
            identifier = '[".tuple", %s, %d]' % (name, id(self.ext_val))
            yield (common_serialization.SerializableDummy, [self.ext_val],
                   str, ['[".ext", %s]' % identifier], False)

        ### Freezing-Only Types ###

        if freezing:
            mod_name = "feat.test.test_common_serialization_json"
            fun_name = '"%s.dummy_function"' % mod_name
            meth_name = '"%s.DummyClass.dummy_method"' % mod_name

            yield types.FunctionType, [dummy_function], str, [fun_name], True

            yield (types.FunctionType, [DummyClass.dummy_method],
                   str, [meth_name], True)

            o = DummyClass()
            yield types.FunctionType, [o.dummy_method], str, [meth_name], True

        #### Basic mutable types plus tuples ###

        # Exception for empty tuple singleton
        yield tuple, [()], str, ['[".tuple"]'], False
        yield tuple, [(1, 2, 3)], str, ['[".tuple", 1, 2, 3]'], True
        yield list, [[]], str, ['[]'], True
        yield list, [[1, 2, 3]], str, ['[1, 2, 3]'], True
        yield set, [set([])], str, ['[".set"]'], True
        yield set, [set([1, 3])], str, ['[".set", 1, 3]'], True
        yield dict, [{}], str, ['{}'], True
        yield dict, [{"1": 2, "3": 4}], str, ['{"1": 2, "3": 4}'], True

        # Container with different types
        yield (tuple, [(0.11, "a", u"z", False, None,
                        (1, ), [2], set([3]), {"4": 5})],
               str, ['[".tuple", 0.11, [".enc", "UTF8", "a"], "z", false, '
                     'null, [".tuple", 1], [2], [".set", 3], {"4": 5}]'], True)
        yield (list, [[0.11, "a", u"z", False, None,
                       (1, ), [2], set([3]), {"4": 5}]],
               str, ['[0.11, [".enc", "UTF8", "a"], "z", false, null, '
                     '[".tuple", 1], [2], [".set", 3], {"4": 5}]'], True)

        ### References and Dereferences ###

        # Simple reference in list
        a = []
        b = [a, a]
        yield list, [b], str, ['[[".ref", 1, []], [".deref", 1]]'], True

        # Simple reference in tuple
        a = ()
        b = (a, a)
        yield tuple, [b], str, ['[".tuple", [".ref", 1, [".tuple"]], '
                                '[".deref", 1]]'], True

        # Simple dereference in dict value.
        a = []
        b = [a, {"1": a}]
        yield list, [b], str, ['[[".ref", 1, []], {"1": [".deref", 1]}]'], True

        # Simple reference in dict value.
        a = []
        b = [{"1": a}, a]
        yield list, [b], str, ['[{"1": [".ref", 1, []]}, [".deref", 1]]'], True

        # Multiple reference in dictionary values, because dictionary order
        # is not predictable all possibilities have to be tested
        a = {}
        b = {"1": a, "2": a, "3": a}
        yield (dict, [b], str,
            ['{"1": [".ref", 1, {}], "2": [".deref", 1], "3": [".deref", 1]}',
             '{"1": [".ref", 1, {}], "3": [".deref", 1], "2": [".deref", 1]}',
             '{"2": [".ref", 1, {}], "1": [".deref", 1], "3": [".deref", 1]}',
             '{"2": [".ref", 1, {}], "3": [".deref", 1], "1": [".deref", 1]}',
             '{"3": [".ref", 1, {}], "1": [".deref", 1], "2": [".deref", 1]}',
             '{"3": [".ref", 1, {}], "2": [".deref", 1], "1": [".deref", 1]}'],
               True)

        # Simple dereference in set.
        a = ()
        b = [a, set([a])]
        yield list, [b], str, ['[[".ref", 1, [".tuple"]], '
                               '[".set", [".deref", 1]]]'], True

        # Simple reference in set.
        a = ()
        b = [set([a]), a]
        yield list, [b], str, ['[[".set", [".ref", 1, [".tuple"]]], '
                               '[".deref", 1]]'], True

        # Multiple reference in set, because set values order
        # is not predictable all possibilities have to be tested
        a = ()
        b = set([(1, a), (2, a)])
        yield (set, [b], str,
               ['[".set", [".tuple", 1, [".ref", 1, [".tuple"]]], '
                '[".tuple", 2, [".deref", 1]]]',
                '[".set", [".tuple", 2, [".ref", 1, [".tuple"]]], '
                '[".tuple", 1, [".deref", 1]]]'], True)

        # List self-reference
        a = []
        a.append(a)
        yield list, [a], str, ['[".ref", 1, [[".deref", 1]]]'], True

        # Dict self-reference
        a = {}
        a["1"] = a
        yield dict, [a], str, ['[".ref", 1, {"1": [".deref", 1]}]'], True

        # Multiple references
        a = []
        b = [a]
        c = [a, b]
        d = [a, b, c]
        yield list, [d], str, ['[[".ref", 1, []], '
                               '[".ref", 2, [[".deref", 1]]], '
                               '[[".deref", 1], [".deref", 2]]]'], True

        # Default instance
        o = DummyClass()
        o.value = 42

        if freezing:
            yield (DummyClass, [o], str, ['{"value": 42}'], True)
        else:
            name = reflect.canonical_name(o)
            yield (DummyClass, [o], str,
                   ['{".type": "%s", "value": 42}' % name,
                    '{"value": 42, ".type": "%s"}' % name], True)

        Klass = DummyClass
        name = reflect.canonical_name(Klass)

        a = Klass()
        b = Klass()
        c = Klass()

        a.ref = b
        b.ref = a
        c.ref = c

        if freezing:
            yield (Klass, [a], str,
                   ['[".ref", 1, {"ref": {"ref": [".deref", 1]}}]'], True)
            yield (Klass, [b], str,
                   ['[".ref", 1, {"ref": {"ref": [".deref", 1]}}]'], True)
            yield (Klass, [c], str,
                   ['[".ref", 1, {"ref": [".deref", 1]}]'], True)

        else:
            yield (Klass, [a], str,
                   [('[".ref", 1, {".type": "%s", "ref": {".type": "%s", '
                     '"ref": [".deref", 1]}}]') % (name, name)], True)
            yield (Klass, [b], str,
                   [('[".ref", 1, {".type": "%s", "ref": {".type": "%s", '
                     '"ref": [".deref", 1]}}]') % (name, name)], True)
            yield (Klass, [c], str, [('[".ref", 1, {".type": "%s", "ref": '
                                      '[".deref", 1]}]') % (name, )], True)
