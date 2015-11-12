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

from zope.interface import Attribute

from serialization.interface import protocols, requests

__all__ = ["IRequesterFactory", "IAgencyRequester", "IAgentRequester"]


class IRequesterFactory(protocols.IInitiatorFactory):
    '''This class is used to create instances of a requester
    implementing L{IAgentRequester}. Used by the agency when
    initiating a request.'''


class IAgencyRequester(requests.IRequestPeer):

    '''Agency part of a requester. Used by L{IAgentRequester} to perform
    the requester role of the request protocol.'''

    def request(request):
        '''Post a request message.'''

    def initiate(requester):
        '''
        Called by AgencyAgent to pass the L{IAgentRequester} instance
        and perform all the necesseary setup.
        @param requester: requester instance
        @type requester: L{IAgentRequester}
        '''

    def get_recipients():
        '''
        @return: The recipients of the request
        @rtype: IRecipient
        '''


class IAgentRequester(protocols.IInitiator):
    '''Agent part of the requester. It uses an instance implementing
    L{IAgencyRequester} given at creation time as a medium to perform
    the requester role of the request protocol.'''

    protocol_id = Attribute('Defines whan particular request it is')
    timeout = Attribute('Number of seconds after which contract expires.\
                         Default=0 means no timeout')

    def initiate(*args, **kwargs):
        pass

    def got_reply(reply):
        pass

    def closed():
        """
        Called when the request expire or there is no more reply expected.
        """
