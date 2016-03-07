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

from six.moves import builtins
from functools import wraps
import inspect
import sys
import types
from future.utils import PY3

from zope.interface.interface import InterfaceClass


def canonical_name(obj):
    if isinstance(obj, types.MethodType):
        return _canonical_method(obj)

    if isinstance(obj, (type, types.FunctionType, InterfaceClass)):
        return _canonical_type(obj)

    if isinstance(obj, type(None)):
        return _canonical_none(obj)

    if isinstance(obj, types.BuiltinFunctionType):
        return _canonical_builtin(obj)

    return _canonical_type(obj.__class__)


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


@unicode_args
def named_module(name):
    """Returns a module given its name."""
    module = __import__(name)
    packages = name.split(".")[1:]
    m = module
    for p in packages:
        m = getattr(m, p)
    return m


@unicode_args
def named_object(name):
    """Gets a fully named module-global object."""
    name_parts = name.split('.')
    module = named_module('.'.join(name_parts[:-1]))
    return getattr(module, name_parts[-1])


def class_locals(depth, tag=None):
    frame = sys._getframe(depth)
    locals = frame.f_locals
    # Try to make sure we were called from a class def. In 2.2.0 we can't
    # check for __module__ since it doesn't seem to be added to the locals
    # until later on.  (Copied From zope.interfaces.declartion._implements)
    if (locals is frame.f_globals) or (
            ('__module__' not in locals) and sys.version_info[:3] > (2, 2, 0)):
        name = (tag and tag + " ") or ""
        raise TypeError(name + "can be used only from a class definition.")
    return locals


### Private Methods ###


def _canonical_type(obj):
    return obj.__module__ + "." + getattr(obj, '__qualname__', obj.__name__)


def _canonical_none(obj):
    return None


def _canonical_method(obj):
    if PY3:
        return _canonical_type(obj)
    return _canonical_type(obj.im_class) + "." + obj.__name__


def _canonical_builtin(obj):
    return builtins.__name__ + '.' + obj.__name__
