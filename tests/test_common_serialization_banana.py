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

from serialization.common import error
import unittest

try:
    from serialization import banana
except error.SerializeCompatError as err:
    banana = None
    skip_msg = str(err)

from serialization.interface.serialization import *

from . import common_serialization


class BananaConvertersTest(common_serialization.ConverterTest):

    def setUp(self):
        if banana is None:
            raise unittest.SkipTest(skip_msg)
        common_serialization.ConverterTest.setUp(self)
        ext = self.externalizer
        self.serializer = banana.Serializer(externalizer=ext)
        self.unserializer = banana.Unserializer(externalizer=ext)

    def testHelperFunctions(self):
        self.checkSymmetry(banana.serialize, banana.unserialize)
