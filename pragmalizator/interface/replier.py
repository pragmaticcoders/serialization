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
from serialization.interface import protocols, requests

__all__ = ["IReplierFactory", "IAgencyReplier", "IAgentReplier"]


class IReplierFactory(protocols.IInterest):
    '''This class constructs replier instances implementing
    L{IAgentReplier}. Used upon receiving request messages.
    It is passed as a parameter during registration of interest'''


class IAgencyReplier(requests.IRequestPeer):
    '''Agency part of a request replier. Used by L{IAgentReplier} in order
    to perform the replier role in the request protocol.'''

    def reply(reply):
        pass


class IAgentReplier(protocols.IInterested):
    '''Agent part of the request replier. Uses a reference to L{IAgencyReplier}
    given at creation time as a medium in order to perform the replier role
    in the request protocol.'''

    def requested(request):
        pass
