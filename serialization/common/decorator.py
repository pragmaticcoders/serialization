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

from functools import wraps

"""TODO: Better function mimicry."""


def simple_class(decorator):
    '''Decorator used to make simple class decorator without arguments.
    Doesn't really do anything, just here to have a central
    implementation of the simple class decorator.'''

    def meta_decorator(cls):
        return decorator(cls)

    return meta_decorator


def parametrized_class(decorator):
    '''Decorator used to make simple class decorator with arguments.
    Doesn't really do anything, just here to have a central
    implementation of the simple class decorator.'''

    def decorator_builder(*args, **kwargs):

        def meta_decorator(cls):
            return decorator(cls, *args, **kwargs)

        return meta_decorator

    return decorator_builder


def simple_function(decorator):
    '''Decorator used to create decorators without arguments.
    Should be used with function returning another function
    that will be called with the original function has the first
    parameter.
    No difference are made between method and function,
    so the wrapper function will have to know if the first
    argument is an instance (self).

    Note that when using reflect or annotate module functions,
    depth should be incremented by one.

    Example::

        @decorator.simple_function
        def mydecorator(function_original):

            def wrapper(call, arguments):
                # processing
                return function_original(call, arguments)

            return wrapper

        @mydecorator
        def myfunction():
            pass

    '''

    def meta_decorator(function):
        return _function_mimicry(function, decorator(function))

    return meta_decorator


def unicode_args(fn):
    @wraps(fn)
    def wrapper(*orig_args, **orig_kwargs):
        args = []
        for a in orig_args:
            if isinstance(a, bytes):
                arg = a.decode()
            else:
                arg = a
            args.append(arg)
        kwargs = {}
        for k, v in orig_kwargs.items():
            if isinstance(v, bytes):
                value = v.decode()
            else:
                value = v
            kwargs[k] = value
        return fn(*args, **kwargs)
    return wrapper


### Private ###


def _function_mimicry(original, mimic):
    # FIXME: We should do better and to copy function signature too
    mimic.original_func = original
    if original.__dict__:
        for key in original.__dict__:
            setattr(mimic, key, original.__dict__[key])
    mimic.__name__ = original.__name__
    mimic.__doc__ = original.__doc__
    return mimic
