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

from zope.interface import Interface, Attribute

from serialization.common import error


__all__ = ["IPeerInfo"]


class SecurityError(error.FeatError):
    pass


class IPeerInfo(Interface):

    identity = Attribute("Name uniquely identifying a user")
    email = Attribute("User email address")
    context = Attribute("String uniquely identifying security context; "
                        "For example it could be the concatenation of the "
                        "elements taking part in identifying a security "
                        "context, like identity and roles.")

    def has_role(role):
        """@return: if the peer have the specified role."""

    def iter_roles():
        """@return: an iterator over peer's roles."""
