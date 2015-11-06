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

from twisted.python import failure

from feat.common import serialization, adapter, defer
from feat.common.serialization import base, sexp, adapters

from feat.interface.serialization import *

from . import common


class DummyError(Exception):

    def __init__(self, custom, values, *args):
        Exception.__init__(self, *args)
        self.custom = custom
        self.value = values


class SomeException(Exception):
    pass


class OtherException(Exception):
    pass


class TestAdapters(common.TestCase):

    def setUp(self):
        self.serializer = sexp.Serializer()
        self.unserializer = sexp.Unserializer()

    def pingpong(self, value):
        data = self.serializer.convert(value)
        return self.unserializer.convert(data)

    def testExceptionAdapter(self):
        value1 = ValueError("some", "argument", 42)
        result1a = self.pingpong(value1)
        self.assertTrue(isinstance(result1a, type(value1)))
        self.assertEqual(result1a, value1)
        result1b = self.pingpong(result1a)
        self.assertTrue(isinstance(result1b, type(value1)))
        self.assertEqual(result1b, value1)
        self.assertEqual(result1b, result1a)
        self.assertEqual(type(result1b), type(result1a))
        self.assertEqual(type(result1a).__bases__[0], type(value1))
        self.assertEqual(type(result1b).__bases__[0], type(value1))

        value2 = DummyError("some", "argument", 42)
        result2 = self.pingpong(value2)
        self.assertTrue(isinstance(result2, type(value2)))
        self.assertEqual(result2, value2)

        self.assertNotEqual(result1a, result2)

    def testUnserializeUnicodeError(self):
        a = ('{'
                '".state": [".tuple", ['
                    '".type", "exceptions.UnicodeEncodeError"], '
                    '[".tuple", "ascii", '
                        '"DataX does not confirm the data for '
                        'XXXX/YYYYYYY/1234. '
                        'Match code=0", 44, 46, "ordinal not in range(128)"],'
                        ' {}], '
                '".type": "exception"}')
        ex = self.unserializer.convert(a)
        str(ex) # this line was causing seg fault before the fix

    def testFailures(self):
        # Create a true failure
        try:
            1 + ""
        except TypeError, e:
            value1 = failure.Failure(e)

        result1a = self.pingpong(value1)
        self.assertTrue(issubclass(type(result1a), failure.Failure))
        self.assertEqual(result1a, value1)
        result1b = self.pingpong(result1a)
        self.assertTrue(isinstance(result1b, failure.Failure))
        self.assertEqual(result1b, value1)
        self.assertEqual(result1b, result1a)
        self.assertEqual(type(result1b), type(result1a))
        self.assertEqual(type(result1a).__bases__[0], failure.Failure)
        self.assertEqual(type(result1b).__bases__[0], failure.Failure)

    def testTrapingFailureAdapter(self):
        f = failure.Failure(SomeException("not trapped"))
        adapter = ISerializable(f)
        self.assertIsInstance(adapter, adapters.FailureAdapter)

        d = defer.Deferred()
        d.addErrback(adapters.FailureAdapter.trap, OtherException)

        d.errback(adapter)
        self.assertFailure(d, SomeException)
        return d
