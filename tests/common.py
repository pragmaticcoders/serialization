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
import sys

from serialization.common import log


class TestCase(unittest.TestCase, log.LogProxy, log.Logger):

    log_category = "test"

    # define names of class variables here, which values can be change
    # with the @attr decorator
    configurable_attributes = []
    skip_coverage = False

    def __init__(self, *args, **kwargs):
        log_keeper = log.get_default() or log.FluLogKeeper()
        unittest.TestCase.__init__(self, *args, **kwargs)
        log.LogProxy.__init__(self, log_keeper)
        log.Logger.__init__(self, self)

    @classmethod
    def setUpClass(cls):
        if cls is TestCase or hasattr(cls, 'abstract'):
            raise unittest.SkipTest(
                "Skip {} tests, it's a base class".format(cls)
            )
        super(TestCase, cls).setUpClass()

    def assert_not_skipped(self):
        if self.skip_coverage and sys.gettrace():
            raise unittest.SkipTest("Test Skipped during coverage")

    def setUp(self):
        log.test_reset()
        self.assert_not_skipped()

    def assertFails(self, exception_class, method, *args, **kwargs):
        d = method(*args, **kwargs)
        self.assertFailure(d, exception_class)
        return d

    def stub_method(self, obj, method, handler):
        handler = functools.partial(handler, obj)
        obj.__setattr__(method, handler)
        return obj

    def tearDown(self):
        log.test_reset()
