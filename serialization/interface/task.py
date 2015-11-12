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

from zope.interface import Attribute, Interface

from serialization.interface import protocols

__all__ = ["ITaskFactory", "IAgencyTask", "IAgentTask", "NOT_DONE_YET"]


NOT_DONE_YET = "___not yet___"


class ITaskFactory(protocols.IInitiatorFactory):
    '''This class is used to create instances of a task
    implementing L{IAgentTask}. Used by the agency
    when initiating a task.'''


class IAgencyTask(protocols.IAgencyProtocol):
    '''Agency part of a task manager'''

    def finished():
        '''
        Returns boolean saying if the task is still working.
        '''


class IAgentTask(protocols.IInitiator):
    '''Agent part of the task manager'''

    timeout = Attribute('Timeout')

    def initiate():
        '''
        Called as the entry point for the task. This method should return
        a Fiber. If the result of the fiber is NOT_DONE_YET, it will not
        finish right away.
        '''

    def expired():
        '''Called when the task has been not done
        before time specified with the L{timeout} attribute.'''
