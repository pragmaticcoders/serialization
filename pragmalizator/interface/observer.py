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

__all__ = ["IObserver"]


class IObserver(Interface):
    '''
    Wraps the asynchronous job remembering it status and result.
    '''

    def notify_finish(self):
        '''
        Gives a fiber which will fire when the observed job is done (or is
        fired instantly). The fibers trigger value and status should be the
        same as the result of the asynchronous job.
        '''

    def active(self):
        '''
        Returns True/False saying if the job is still being performed.
        '''

    def get_result(self):
        '''
        Get the result synchronously. It may only be called after the job
        has finished. Overwise it should raise runtime error.
        If the job failed this method returns the Failure instance.

        @raises RuntimeError
        '''
