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

from serialization.interface import protocols, contracts

__all__ = ["IContractorFactory", "IAgencyContractor", "IAgentContractor"]


class IContractorFactory(protocols.IInterest):
    '''This class constructs contractor instance implementing
    L{IAgentContractor}. Used upon receiving announce messages.
    It is passed as a parameter during registration of interest'''

    def __call__(agent, medium, *args, **kwargs):
        pass


class IAgencyContractor(contracts.IContractPeer):
    '''This is the agency part of a contractor, the medium between the agent
    and the agency. It is used by L{IAgentContractor} implementations
    to perform the contractor role of the contract protocol'''

    def bid(bid):
        '''Puts a bid on the announcement'''

    def handover(bid):
        '''
        Sends the bid received from the nested contractor. The reply-to field
        is preserved, so the rest of dialog will be delegated to the nested
        contractor. For us this means end of story.
        '''

    def refuse(refusal):
        '''Refuses the announcement'''

    def defect(cancellation):
        '''Cancels the granted job'''

    def complete(report):
        '''Reports a completed job'''

    def update_manager_address(recipient):
        '''Call it to notify the agency that manager is available now
        at different address.'''


class IAgentContractor(protocols.IInterested):
    '''This is agent part of a contractor. It use a reference to a
    L{IAgencyContractor} given at construction time as a medium in order
    to perform the contractor role of the contract protocol.'''

    ack_timeout = Attribute('How long to wait for ack after sending'
                            'the report before aborting')
    bid_timeout = Attribute('How long to wait for grant or rejection '
                            'after putting the bid')

    def announced(announce):
        '''Called by the agency when a contract matching
        the contractor has been received. Called only once.

        @type  announce: L{serialization.agents.message.Announcement}
        '''

    def announce_expired():
        pass

    def rejected(rejection):
        pass

    def granted(grant):
        pass

    def bid_expired():
        pass

    def cancelled(grant):
        pass

    def acknowledged(grant):
        pass

    def aborted():
        pass
