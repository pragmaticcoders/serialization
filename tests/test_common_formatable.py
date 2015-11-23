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

from . import common

import serialization
from serialization.common import formatable


@serialization.register
class Base(formatable.Formatable):

    formatable.field('field1', None)
    formatable.field('field2', 5, 'custom_serializable')


@serialization.register
class Child(Base):

    formatable.field('field1', 'overwritten default')
    formatable.field('field3', None)


@serialization.register
class PropertyTest(formatable.Formatable):

    formatable.field('array', list())

    @property
    def element(self):
        return self.array and self.array[-1]

    @element.setter
    def element(self, value):
        self.array.append(value)

    @property
    def readonly(self):
        return 'readonly'


class TestFormatable(common.TestCase):

    def setUp(self):
        pass

    def testConstructing(self):
        base = Base(field1=2)
        self.assertEqual(2, base.field1)
        self.assertEqual(5, base.field2)

        self.assertEquals(2, len(base._fields))

        def get_field3(instance):
            return instance.field3

        self.assertRaises(AttributeError, get_field3, base)

    def testOverwritedDefault(self):
        child = Child()
        self.assertEqual('overwritten default', child.field1)

    def testUnknownAttributesInContructor(self):

        def construct():
            i = Base(unknown_field=2)
            return i

        self.assertRaises(AttributeError, construct)

    def testSnapshot(self):
        base = Base(field1=2)
        snapshot = base.snapshot()
        self.assertIsInstance(snapshot, dict)
        self.assertIn('custom_serializable', snapshot)
        self.assertEqual(5, snapshot['custom_serializable'])
        self.assertIn('field1', snapshot)
        self.assertEqual(2, snapshot['field1'])

    def testDefaultValueOverridenWithNone(self):
        base = Base(field2=None)
        snapshot = base.snapshot()
        self.assertIsInstance(snapshot, dict)
        self.assertIn('custom_serializable', snapshot)
        self.assertEqual(None, snapshot['custom_serializable'])
        self.assertNotIn('field1', snapshot)

    def testRecover(self):
        snapshot = dict(field1=5, custom_serializable=4, field3=1)
        instance = Child.__new__(Child)
        instance.recover(snapshot)
        self.assertEqual(5, instance.field1)
        self.assertEqual(4, instance.field2)
        self.assertEqual(1, instance.field3)

    def testRecoverNoneValueOverridenWithNone(self):
        snapshot = dict(field1=5, custom_serializable=None)
        instance = Base.__new__(Base)
        instance.recover(snapshot)
        self.assertEqual(5, instance.field1)
        self.assertEqual(None, instance.field2)

    def testNoneValues(self):
        base = Base(field1=0, field2=[])
        self.assertEqual(0, base.field1)
        self.assertEqual([], base.field2)

    def testPropertySetters(self):
        a = PropertyTest(element=2)
        self.assertEqual([2], a.array)
        self.assertEqual(2, a.element)

        self.assertRaises(AttributeError, PropertyTest, readonly=2)
