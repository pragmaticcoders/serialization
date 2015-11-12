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
from zope.interface import Interface, Attribute

from serialization.common import enum
from serialization.interface import protocols

__all__ = ["ContractState", "IContractPeer"]


class ContractState(enum.Enum):
    '''Contract protocol state:

    For manager:

     - initiated:    The manager has been initiated but didn't publish any
                      announcement yet.
     - announced:    The manager published an announcement to contractors.
     - closed:       The contract has been closed because the announce expired
                      or a response has been received from all involved
                      contractors.
     - terminated:   The manager has been terminated by agent-side code.
     - granted:      The contract has been granted to one or multiple
                      contractor.
     - expired:      Contract expire without granting any bid.
     - completed:    All granted jobs have been acknowledged by the manager.
     - cancelled:    Some contractor didn't report in time so all contractors
                      got cancelled.
     - aborted:      Some jobs have been cancelled so all the contractors
                      got cancelled.
     - wtf:          What a Terrible Failure
     - bid:          Only for contractors, invalid state for managers.
     - refused:      Only for contractors, invalid state for managers.
     - rejected:     Only for contractors, invalid state for managers.
     - defected:     Only for contractors, invalid state for managers.
     - acknowledged: Only for contractors, invalid state for managers.


    For contractor:
     - initiated:    The contractor is created, the announce message is not
                      parsed yet.
     - announced:    The manager published an announcement
     - closed:       The Announce expired without putting bid nor refusal.
     - bid:          A bid has been put on an announcement.
     - refused:      The announce has been refused.
     - delegated:    The bid created by the nested contractor has been sent.
     - rejected:     The bid has been rejected by the manager.
     - granted:      The contract has been granted.
     - expired:      Bid expired without grant nor rejection.
     - completed:    Granted job is completed.
     - cancelled:    The manager cancelled the job.
     - defected:     The contractor renounced and sent a cancellation
                     to the manager.
     - acknowledged: The manager acknowledged the completed job.
     - aborted:      The manager has not acknowledged the report in time,
                      or explicitly canceled the job.
     - wtf:          What a Terrible Failure
    '''
    (initiated, announced, closed, bid, refused, delegated, rejected, granted,
     expired, completed, terminated, defected, cancelled, acknowledged,
     aborted, wtf) = range(16)


class IContractPeer(protocols.IAgencyProtocol):
    '''Define common interface between both peers of the contract protocol.'''

    agent = Attribute("Reference to the owner agent")
