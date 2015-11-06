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

from pragmalizator.common import enum

__all__ = ["RecipientType", "IRecipients", "IRecipient"]


'''
Provides interfaces for specifing the recipients of messages.
Types that can be passed as destination includes:

- Agent (defined in this module)
- Broadcast (defined in this module)
- agent.IAgencyAgent this helps in tests - one can say that is sending message
                     to the agent
- message.BaseMessage (and subclasses) - one can say he is responding
                                         to message
- list - the list of any combination of above
'''


class RecipientType(enum.Enum):
    agent, broadcast = range(1, 3)


class IRecipients(Interface):
    '''Iterable with all elements implementing IRecipient'''

    def __iter__(self):
        pass


class IRecipient(Interface):

    shard = Attribute('Shard of recipient. DEPRECATED, use route instead.')
    route = Attribute("Recipient's route (shard or connection string)")
    key = Attribute("Routing key of recipient.")
    type = Attribute("Recipient's type (RecipientType).")
    channel = Attribute("Communication channel name.")
