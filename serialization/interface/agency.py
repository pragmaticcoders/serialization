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
from zope.interface import Interface
from serialization.common import enum


__all__ = ["ExecMode", "IAgency"]


class ExecMode(enum.Enum):
    '''
    Used for registering the dependencies.
    '''

    production, test, simulation = range(3)


class IAgency(Interface):
    '''The agency. It manages agents communications, state, log, journal...
    It only publishes the interface global for all agents, agent normally use
    there L{IAgencyAgent} reference given at initialization time.'''

    def start_agent(descriptor, **kwargs):
        '''
        Start new agent for the given descriptor.
        The factory is lookuped at in the agents registry.
        The kwargs will be passed to the agents initiate_agent() method.

        @rtype: L{IAgencyAngent}
        '''

    def get_time():
        '''
        Use this to get current time. Should fetch the time from NTP server
        @returns: Number of seconds since epoch
        '''

    def set_mode(component, mode):
        '''
        Tell in which mode should the given componenet operate.
        @param component: String representing the component.
        @param mode: L{ExecMode}
        '''

    def get_mode(component):
        '''
        Get the mode to run given component.
        '''

    def get_config():
        '''
        Returns the agency config.
        @rtype: serialization.agencies.net.config.AgencyConfig
        '''
