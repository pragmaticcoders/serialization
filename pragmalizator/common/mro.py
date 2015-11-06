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

import inspect
import sys

from pragmalizator.common import fiber, defer


class Common(object):

    __slots__ = ()

    def _get_mro_call_list(self, method_name, keywords, raise_on_unconsumed):
        cls = type(self)
        klasses = list(cls.mro())
        klasses.reverse()

        call_list = list()

        consumed_keys = set()
        for klass in klasses:
            method = klass.__dict__.get(method_name, None)
            if not method:
                continue
            if hasattr(method, 'original_func'):
                function = method.original_func
            else:
                function = method

            argspec = inspect.getargspec(function)
            defaults = argspec.defaults and list(argspec.defaults) or list()
            kwargs = dict()
            for arg, default_index in zip(argspec.args,
                                          range(-len(argspec.args), 0)):
                if arg in ['self', 'state']:
                    continue
                if arg in keywords:
                    consumed_keys.add(arg)
                    kwargs[arg] = keywords[arg]
                else:
                    try:
                        kwargs[arg] = defaults[default_index]
                    except IndexError:
                        msg = ("Missing value for keyword argument %s "
                               "of the method %r" % (arg, method))
                        raise AttributeError(msg), None, sys.exc_info()[2]

            call_list.append((method, kwargs, ))

        diff = set(keywords.keys()) - consumed_keys
        if raise_on_unconsumed and diff:
            msg = ('Unconsumed arguments %r while calling mro method %s' %
                   (diff, method_name))
            raise AttributeError(msg)

        return call_list


class FiberMroMixin(Common):

    __slots__ = ()

    def call_mro(self, method_name, **keywords):
        return self.call_mro_ex(method_name, keywords, _debug_depth=1)

    def call_mro_ex(self, method_name, keywords,
                    raise_on_unconsumed=True, _debug_depth=0):
        f = fiber.succeed(debug_depth=_debug_depth+1)
        call_list = self._get_mro_call_list(
            method_name, keywords, raise_on_unconsumed)
        for method, kwargs in call_list:
            f.add_callback(fiber.drop_param, method, self, **kwargs)
        return f


class DeferredMroMixin(Common):

    __slots__ = ()

    def call_mro(self, method_name, **keywords):
        return self.call_mro_ex(method_name, keywords)

    def call_mro_ex(self, method_name, keywords, raise_on_unconsumed=True):
        d = defer.succeed(None)
        call_list = self._get_mro_call_list(
            method_name, keywords, raise_on_unconsumed)
        for method, kwargs in call_list:
            d.addCallback(defer.drop_param, method, self, **kwargs)
        return d
