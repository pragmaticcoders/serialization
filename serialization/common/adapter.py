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

from zope.interface import adapter, interface, declarations

registry = adapter.AdapterRegistry()


def _lookup_adapter_hook(iface, ob):
    factory = registry.lookup1(declarations.providedBy(ob), iface)
    return factory and factory(ob)

interface.adapter_hooks.append(_lookup_adapter_hook)


def register(adapted, interface):

    def register(cls):
        register_adapter(registry, cls, adapted, interface)
        return cls
    return register


def register_adapter(registry, adapter_factory, adapted, *interfaces):
    assert interfaces, "You need to pass an Interface"

    # deal with class->interface adapters:
    if not isinstance(adapted, interface.InterfaceClass):
        adapted_ = declarations.implementedBy(adapted)
    else:
        adapted_ = adapted

    for iface in interfaces:
        factory = registry.registered([adapted_], iface)
        if factory is not None:
            raise ValueError("an adapter (%s) was already registered."
                             % (factory, ))
    for iface in interfaces:
        registry.register([adapted_], iface, '', adapter_factory)

    return adapter_factory
