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
from pragmalizator.common import enum

from pragmalizator.interface import protocols

__all__ = ["RequestState", "IRequestPeer"]


class RequestState(enum.Enum):
    '''
    Request protocol state:

      - none: Not initiated.
      - requested: The requested has send a request message to to repliers.
      - closed: The request expire or a response has been received
        from all repliers.
      - wtf: What a Terrible Failure
      - terminated: the protocol has been terminated while requested
    '''
    none, requested, closed, wtf, terminated = range(5)


class IRequestPeer(protocols.IAgencyProtocol):
    '''Define common interface between both peers of the request protocol.'''
