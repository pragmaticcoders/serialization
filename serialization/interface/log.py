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

from zope.interface import Interface, Attribute

from serialization.common import enum

__all__ = ["LogLevel", "ILogKeeper", "ILogger"]


class LogLevel(enum.Enum):
    error, warning, info, debug, log = range(1, 6)


class ILogKeeper(Interface):
    '''Store logging entries'''

    def do_log(level, object, category, format, args,
               depth=1, file_path=None, line_num=None):
        '''Adds a log entry with specified level, category and object.
        @param depth: The depth in the calling stack from the logging call.
        @type  depth: int
        @param file_path: file to show the message as coming from, if caller
                          knows best
        @type  file_path: str
        @param line_num: line to show the message as coming from, if caller
                         knows best
        @type  line_num: int
        '''


class ILogger(Interface):
    '''Can be used to generate contextual logging entries'''

    logname = Attribute("Logging name")

    def log(format, *args):
        pass

    def debug(format, *args):
        pass

    def info(format, *args):
        pass

    def warning(format, *args):
        pass

    def error(format, *args):
        pass

    def logex(level, format, args, depth=1):
        '''Extended logging. Allows changing stack depth.'''
