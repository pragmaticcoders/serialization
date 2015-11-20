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

import functools
import unittest


class TestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if cls is TestCase:
            cls.skipBaseClass()
        super(TestCase, cls).setUpClass()

    @classmethod
    def skipBaseClass(cls):
        raise unittest.SkipTest(
            "Skip {} tests, it's a base class".format(cls)
        )

    def assertFails(self, exception_class, method, *args, **kwargs):
        d = method(*args, **kwargs)
        self.assertFailure(d, exception_class)
        return d

    def stub_method(self, obj, method, handler):
        handler = functools.partial(handler, obj)
        obj.__setattr__(method, handler)
        return obj
