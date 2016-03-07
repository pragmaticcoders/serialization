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

# See 'LICENSE.GPL' in the source distribution for more information.

# Headers in this file shall remain intact.
# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import pytest
from serialization import reflect
from six.moves import builtins
from zope.interface import Interface


class DummyInterface(Interface):
    pass


class Dummy(object):

    def spam(self):
        pass


def bacon():
    pass


class Meta(type):
    pass


class MetaDummy(object):
    __metaclass__ = Meta


class TestIntrospection(object):

    @pytest.fixture(scope='session')
    def builtin_module(self):
        return builtins.__name__

    def test_interface(self):
        assert (
            'tests.test_reflect.DummyInterface' ==
            reflect.canonical_name(DummyInterface))

    def test_class(self, builtin_module):
        assert 'tests.test_reflect.Dummy' == reflect.canonical_name(Dummy)
        assert 'tests.test_reflect.Dummy' == reflect.canonical_name(Dummy())
        assert builtin_module + '.int' == reflect.canonical_name(int)
        assert builtin_module + '.str' == reflect.canonical_name('some string')

    def test_class_with_meta(self):
        assert (
            'tests.test_reflect.MetaDummy' ==
            reflect.canonical_name(MetaDummy))

    def test_method(self, builtin_module):
        assert (
            'tests.test_reflect.Dummy.spam' ==
            reflect.canonical_name(Dummy.spam))
        assert (
            'tests.test_reflect.Dummy.spam' ==
            reflect.canonical_name(Dummy().spam))
        assert (
            builtin_module + '.split' ==
            reflect.canonical_name('test'.split))

    def test_function(self, builtin_module):
        assert 'tests.test_reflect.bacon' == reflect.canonical_name(bacon)
        assert builtin_module + '.getattr' == reflect.canonical_name(getattr)

    def test_none(self):
        assert None == reflect.canonical_name(None)

    def test_class_locals_not_from_class(self):
        with pytest.raises(TypeError):
            reflect.class_locals(depth=2)


def simple(a, b):
    pass


def defaults(a, b=3):
    pass


def varargs(a, b=None, *args):
    pass


def kwargs(a=None, b=3, *args, **kwargs):
    pass
