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

from __future__ import absolute_import

import pytest
# unuse import adapters but its needed
from serialization import sexp, adapters


class DummyError(Exception):

    def __init__(self, custom, values, *args):
        Exception.__init__(self, *args)
        self.custom = custom
        self.value = values


class SomeException(Exception):
    pass


class OtherException(Exception):
    pass


class TestAdapters(object):

    @pytest.fixture
    def serializer(self):
        return sexp.Serializer()

    @pytest.fixture
    def unserializer(self):
        return sexp.Unserializer()

    @pytest.fixture
    def pingpong(self, serializer, unserializer):

        def pingpong(value):
            data = serializer.convert(value)
            return unserializer.convert(data)

        return pingpong

    def test_exception_adapter(self, pingpong):
        value1 = ValueError("some", "argument", 42)
        result1a = pingpong(value1)
        assert isinstance(result1a, type(value1))
        assert result1a == value1
        result1b = pingpong(result1a)
        assert isinstance(result1b, type(value1))
        assert result1b == value1
        assert result1b == result1a
        assert type(result1b) == type(result1a)
        assert type(result1a).__bases__[0] == type(value1)
        assert type(result1b).__bases__[0] == type(value1)

        value2 = DummyError("some", "argument", 42)
        result2 = pingpong(value2)
        assert isinstance(result2, type(value2))
        assert result2 == value2

        assert result1a != result2

    def test_unserialize_unicode_error(self, unserializer):
        a = ('{'
             '".state": [".tuple", ['
             '".type", "exceptions.UnicodeEncodeError"], '
             '[".tuple", "ascii", '
             '"DataX does not confirm the data for '
             'XXXX/YYYYYYY/1234. '
             'Match code=0", 44, 46, "ordinal not in range(128)"],'
             ' {}], '
             '".type": "exception"}')
        ex = unserializer.convert(a)
        str(ex)  # this line was causing seg fault before the fix
