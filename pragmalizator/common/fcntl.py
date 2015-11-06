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
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""Unix-like implementation of pragmalizator.common.fcntl module."""

# Helper functions arround fcntl for file locking
from pragmalizator import hacks

_fcntl = hacks.import_fcntl()
lockf = _fcntl.lockf
flock = _fcntl.flock

# lockf can be used instead, but the lock is shared in the same process,
# as it's taken in the file's inode for the process pid and not in the file
# desctiptor, like flock
LOCK_FN = flock


def lock(fd):
    try:
        LOCK_FN(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        return True
    except IOError:
        return False


def unlock(fd):
    try:
        LOCK_FN(fd, _fcntl.LOCK_UN)
        return True
    except IOError:
        return False
