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

import pytest

import serialization
from serialization import formatable


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


class TestFormatable(object):

    def test_constructing(self):
        base = Base(field1=2)
        assert 2 == base.field1
        assert 5 == base.field2

        assert 2 == len(base._fields)

        def get_field3(instance):
            return instance.field3

        with pytest.raises(AttributeError):
            get_field3(base)

    def test_overwrited_default(self):
        child = Child()
        assert 'overwritten default' == child.field1

    def test_unknown_attributes_in_contructor(self):
        with pytest.raises(AttributeError):
            Base(unknown_field=2)

    def test_snapshot(self):
        base = Base(field1=2)
        snapshot = base.snapshot()
        assert isinstance(snapshot, dict)
        assert 'custom_serializable' in snapshot
        assert 5 == snapshot['custom_serializable']
        assert 'field1' in snapshot
        assert 2 == snapshot['field1']

    def test_default_value_overriden_with_none(self):
        base = Base(field2=None)
        snapshot = base.snapshot()
        assert isinstance(snapshot, dict)
        assert 'custom_serializable' in snapshot
        assert snapshot['custom_serializable'] is None
        assert 'field1' not in snapshot

    def test_recover(self):
        snapshot = dict(field1=5, custom_serializable=4, field3=1)
        instance = Child.__new__(Child)
        instance.recover(snapshot)
        assert 5 == instance.field1
        assert 4 == instance.field2
        assert 1 == instance.field3

    def test_recover_none_value_overriden_with_none(self):
        snapshot = dict(field1=5, custom_serializable=None)
        instance = Base.__new__(Base)
        instance.recover(snapshot)
        assert 5 == instance.field1
        assert None == instance.field2

    def test_none_values(self):
        base = Base(field1=0, field2=[])
        assert 0 == base.field1
        assert [] == base.field2

    def test_property_setters(self):
        a = PropertyTest(element=2)
        assert [2] == a.array
        assert 2 == a.element

        with pytest.raises(AttributeError):
            PropertyTest(readonly=2)
