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
# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.spread import jelly

from feat.common import serialization
from feat.common.serialization import base
from feat.interface.serialization import *

from . import common


class A(serialization.Serializable):

    def __init__(self, x):
        self.x = x


class B(A):

    def __init__(self, x, y):
        A.__init__(self, x)
        self.y = y


class C(serialization.Serializable):

    type_name = "Custom"

    def __init__(self, z):
        self.z = z


class D(serialization.Serializable):

    type_name = "D"

    def __init__(self, u):
        self.u = u

    def recover(self, u):
        self.u = u

    def snapshot(self):
        return self.u


class E(D):

    def __init__(self, u, v):
        D.__init__(self, u)
        self.v = v

    def recover(self, snapshot):
        u, self.v = snapshot
        D.recover(self, u)

    def snapshot(self):
        return D.snapshot(self), self.v


class ListSerializableDummy(serialization.Serializable, jelly.Jellyable):

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


class TestSerializable(common.TestCase):

    def testTypename(self):
        self.assertEqual(A.type_name, __name__ + "." + "A")
        self.assertEqual(B.type_name, __name__ + "." + "B")
        self.assertEqual(C.type_name, "Custom")
        self.assertEqual(D.type_name, "D")
        self.assertEqual(E.type_name, __name__ + "." + "E")

        a = A(42)
        b = B(12, 18)
        c = C(66)
        d = D(1)
        e = E(2, 3)

        self.assertEqual(a.type_name, __name__ + "." + "A")
        self.assertEqual(b.type_name, __name__ + "." + "B")
        self.assertEqual(c.type_name, "Custom")
        self.assertEqual(d.type_name, "D")
        self.assertEqual(e.type_name, __name__ + "." + "E")

    def testSnapshot(self):
        a = A(42)
        self.assertEqual(a.x, 42)
        self.assertEqual(a.snapshot(), {"x": 42})

        b = B(12, 18)
        self.assertEqual(b.x, 12)
        self.assertEqual(b.y, 18)
        self.assertEqual(b.snapshot(), {"x": 12, "y": 18})

        c = C(66)
        self.assertEqual(c.z, 66)
        self.assertEqual(c.snapshot(), {"z": 66})

        d = D(1)
        self.assertEqual(d.u, 1)
        self.assertEqual(d.snapshot(), 1)

        e = E(2, 3)
        self.assertEqual(e.u, 2)
        self.assertEqual(e.v, 3)
        self.assertEqual(e.snapshot(), (2, 3))

    def testRestore(self):
        a = A.restore({"x": 42})
        self.assertEqual(a.x, 42)

        b = B.restore({"x": 12, "y": 18})
        self.assertEqual(b.x, 12)
        self.assertEqual(b.y, 18)

        c = C.restore({"z": 66})
        self.assertEqual(c.z, 66)

        d = D.restore(1)
        self.assertEqual(d.u, 1)

        e = E.restore((2, 3))
        self.assertEqual(e.u, 2)
        self.assertEqual(e.v, 3)

    def testSnapshotRestore(self):
        a1 = A(42)
        a2 = A.restore(a1.snapshot())
        self.assertEqual(a2.x, 42)
        self.assertNotEqual(a1, a2)

        b1 = B(12, 18)
        b2 = B.restore(b1.snapshot())
        self.assertEqual(b2.x, 12)
        self.assertEqual(b2.y, 18)
        self.assertNotEqual(b1, b2)

        c1 = C(66)
        c2 = C.restore(c1.snapshot())
        self.assertEqual(c2.z, 66)
        self.assertNotEqual(c1, c2)

        d1 = D(1)
        d2 = D.restore(d1.snapshot())
        self.assertEqual(d2.u, 1)
        self.assertNotEqual(d1, d2)

        e1 = E(2, 3)
        e2 = E.restore(e1.snapshot())
        self.assertEqual(e2.u, 2)
        self.assertEqual(e2.v, 3)
        self.assertNotEqual(e1, e2)


class DummyVerAdapter1(base.VersionAdapter):
    pass


class DummyVerAdapter2(base.VersionAdapter):

    @staticmethod
    def upgrade_to_3(data):
        data.append("U3")
        return data

    @staticmethod
    def upgrade_to_7(data):
        data.append("U7")
        return data

    @staticmethod
    def upgrade_to_9(data):
        data.append("U9")
        return data

    @staticmethod
    def downgrade_to_2(data):
        data.append("D2")
        return data

    @staticmethod
    def downgrade_to_5(data):
        data.append("D5")
        return data

    @staticmethod
    def downgrade_to_8(data):
        data.append("D8")
        return data


class TestVersionAdapter(common.TestCase):

    def check_combinations(self, adapter, ver_range, expected):
        result = {}
        for a in ver_range:
            for b in ver_range:
                value = adapter.adapt_version([], a, b)
                if value:
                    result[(a, b)] = value

        self.assertEqual(result, expected)

    def testNoAdaption(self):
        self.check_combinations(DummyVerAdapter1, range(1, 10), {})
        self.check_combinations(DummyVerAdapter1(), range(1, 10), {})

    def testDummyAdaption(self):
        expected = {(1, 3): ['U3'],
                    (1, 4): ['U3'],
                    (1, 5): ['U3'],
                    (1, 6): ['U3'],
                    (1, 7): ['U3', 'U7'],
                    (1, 8): ['U3', 'U7'],
                    (1, 9): ['U3', 'U7', 'U9'],
                    (2, 3): ['U3'],
                    (2, 4): ['U3'],
                    (2, 5): ['U3'],
                    (2, 6): ['U3'],
                    (2, 7): ['U3', 'U7'],
                    (2, 8): ['U3', 'U7'],
                    (2, 9): ['U3', 'U7', 'U9'],
                    (3, 1): ['D2'],
                    (3, 2): ['D2'],
                    (3, 7): ['U7'],
                    (3, 8): ['U7'],
                    (3, 9): ['U7', 'U9'],
                    (4, 1): ['D2'],
                    (4, 2): ['D2'],
                    (4, 7): ['U7'],
                    (4, 8): ['U7'],
                    (4, 9): ['U7', 'U9'],
                    (5, 1): ['D2'],
                    (5, 2): ['D2'],
                    (5, 7): ['U7'],
                    (5, 8): ['U7'],
                    (5, 9): ['U7', 'U9'],
                    (6, 1): ['D5', 'D2'],
                    (6, 2): ['D5', 'D2'],
                    (6, 3): ['D5'],
                    (6, 4): ['D5'],
                    (6, 5): ['D5'],
                    (6, 7): ['U7'],
                    (6, 8): ['U7'],
                    (6, 9): ['U7', 'U9'],
                    (7, 1): ['D5', 'D2'],
                    (7, 2): ['D5', 'D2'],
                    (7, 3): ['D5'],
                    (7, 4): ['D5'],
                    (7, 5): ['D5'],
                    (7, 9): ['U9'],
                    (8, 1): ['D5', 'D2'],
                    (8, 2): ['D5', 'D2'],
                    (8, 3): ['D5'],
                    (8, 4): ['D5'],
                    (8, 5): ['D5'],
                    (8, 9): ['U9'],
                    (9, 1): ['D8', 'D5', 'D2'],
                    (9, 2): ['D8', 'D5', 'D2'],
                    (9, 3): ['D8', 'D5'],
                    (9, 4): ['D8', 'D5'],
                    (9, 5): ['D8', 'D5'],
                    (9, 6): ['D8'],
                    (9, 7): ['D8'],
                    (9, 8): ['D8']}

        self.check_combinations(DummyVerAdapter2, range(1, 10), expected)
        self.check_combinations(DummyVerAdapter2(), range(1, 10), expected)
