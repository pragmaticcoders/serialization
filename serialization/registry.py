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


class RegistryEntry(object):

    def __init__(self, obj, key, application):
        self.object = obj
        self.key = key
        self.application = application


class BaseRegistry(object):

    allow_blank_application = True
    verify_interface = None
    key_attribute = None
    allow_none_key = True

    def __init__(self, *data):
        self.reset(data)

    ### IRegistry ###

    def clone(self):
        return type(self)(*self.get_snapshot())

    def get_snapshot(self):
        return self._data.items()

    def reset(self, snapshot):
        self._data = {}  # {key: RegistryEntry}
        for key, entry in snapshot:
            self.register(entry.object,
                          key=entry.key,
                          application=entry.application)

    def register(self, obj, key=None, application=None):
        if self.verify_interface:
            obj = self.verify_interface(obj)
        if application is None and not self.allow_blank_application:
            raise ValueError("Disallowing attemp to register an object %r "
                             "without specifing application owning it")
        if key is None:
            if self.key_attribute:
                key = getattr(obj, self.key_attribute)
            else:
                raise ValueError("Key is missing: %r" % (key, ))
        if key is None and not self.allow_none_key:
            raise ValueError("%r doesn't allows None as the entry key" %
                             (self, ))
        entry = RegistryEntry(obj, key, application)
        self._data[key] = entry
        return obj

    def delete(self, key):
        self._data.pop(key, None)

    def lookup(self, key):
        r = self._data.get(key)
        return r and r.object

    def application_cleanup(self, application):
        for key, entry in self._data.items():
            if entry.application == application:
                del(self._data[key])

    def itervalues(self):
        for r in self._data.itervalues():
            yield r.object
