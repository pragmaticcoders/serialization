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

__all__ = ["JournalMode", "RecordingResultError", "SideEffectResultError",
           "ReentrantCallError", "ReplayError", "NoHamsterballError",
           "IJournalKeeper", "IJournalEntry", "IJournalReplayEntry",
           "IJournalSideEffect", "IEffectHandler",
           "IRecorderNode", "IRecorder"]


class JournalMode(enum.Enum):
    recording, replay = range(1, 3)


class RecordingResultError(RuntimeError):
    pass


class SideEffectResultError(RuntimeError):
    pass


class ReentrantCallError(RuntimeError):
    pass


class ReplayError(BaseException):
    """Inherit from BaseException to not be caught
    by journal exception handler."""


class NoHamsterballError(Exception):
    """
    Thrown when we try to apply entry during replay but don't have any agent
    loaded in the hamsterball.
    """


class IJournalSideEffect(Interface):
    '''Represent a side-effect description in a journal entry.'''

    def add_effect(effect_id, *args, **kwargs):
        pass

    def set_result(result):
        pass

    def get_result():
        pass

    def commit():
        pass


class IJournalReplayEntry(Interface):

    journal_id = Attribute("Instance journal identifier. Read only.")
    function_id = Attribute("Function identifier. Read only.")
    fiber_id = Attribute("Fiber unique identifier. Read only.")
    fiber_depth = Attribute("Fiber depth. Read only.")
    frozen_result = Attribute("Frozen result. Read only.")

    def get_arguments():
        pass

    def get_result():
        pass

    def rewind_side_effects():
        pass

    def next_side_effect(function_id, *args, **kwargs):
        '''Returns the next side-effect result. Used during replay.
        If the parameter do not match the expected ones it could fail.'''


class IJournalEntry(Interface):
    '''Represent an entry in the journal. Every set_* method must be called
    before calling commit().'''

    def set_fiber_context(self, fiber_id, fiber_depth):
        pass

    def new_side_effect(function_id, *args, **kwargs):
        '''Returns a L{IJournalSideEffect} on witch the set_result()
        method should be called, and then commit().'''

    def set_result(result):
        pass

    def commit():
        '''Commit the entry to the journal. The order of the entries
        is not determined by the commit order but by the creation order.'''


class IEffectHandler(Interface):
    '''Used for journal keeper to delegate side-effects effect.'''

    def apply_effect(self, effect_id, *args, **kwargs):
        pass


class IJournalKeeper(Interface):
    '''Store journal entries'''

    def register(recorder):
        '''Adds the specified recorder to the journal keeper registry.
        Should be called by every recorder when created.
        Recorder will be automatically unregistered when they are deleted,
        The journal keeper do not keep strong reference to the recorders.'''

    def new_entry(journal_id, function_id, *args, **kwargs):
        '''Creates a new journal entry. Returns a L{IJournalEntry} that should
        be committed for the entry to be recorded.
        The order of journal entry is determined when calling new_entry()
        and the content is determined when committing it.'''


class IRecorderNode(Interface):

    journal_parent = Attribute('Parent recorder node, L{IRecorderNode} or '
                               'None for the root node')
    journal_keeper = Attribute('Journal keeper to use, L{IJournalKeeper}')

    def generate_identifier(recorder):
        pass


class IRecorder(IRecorderNode):

    journal_id = Attribute('Journal recorder identifier, tuple of int')

    def call(function, args=None, kwargs=None, reentrant=True):
        '''Calls the specified function with arguments and keywords.
        The function have to be the exact registered one, and because
        the decorators are wrapping it inside another function
        calling this method with the instance function will not work.
        If reentrant is False and we already are inside
        a recorded call it will fail with a L{ReentrantCallError}.
        Returns the result of the called function as returned
        by the fiber section.'''

    def record(function, args=None, kwargs=None, reentrant=True):
        '''Calls the function with specified identifier, arguments
        and keywords. If reentrant is False and we already are inside
        a recorded call it will fail with a L{ReentrantCallError}.
        Returns the result of the called function as returned
        by the fiber section.'''

    def replay(fun_id, input):
        '''Calls the function with specified identifier with specified
        input. Input is what was given as a parameter when calling
        IJournalKeeper.record().
        Returns a tuple containing the side effects and the output
        of the function call but do NOT start any asynchronous operation.'''
