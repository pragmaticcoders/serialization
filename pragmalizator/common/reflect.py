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
import types

from zope.interface.interface import InterfaceClass


def canonical_name(obj):
    if isinstance(obj, types.MethodType):
        return _canonical_method(obj)

    if isinstance(obj, (type, types.FunctionType, InterfaceClass)):
        return _canonical_type(obj)

    if isinstance(obj, types.NoneType):
        return _canonical_none(obj)

    if isinstance(obj, types.BuiltinFunctionType):
        return _canonical_builtin(obj)

    return _canonical_type(obj.__class__)


def named_function(name):
    """Gets a fully named module-global object."""
    name_parts = name.split('.')
    module = named_object('.'.join(name_parts[:-1]))
    func = getattr(module, name_parts[-1])
    if hasattr(func, 'original_func'):
        func = func.original_func
    return func


def named_module(name):
    """Returns a module given its name."""
    module = __import__(name)
    packages = name.split(".")[1:]
    m = module
    for p in packages:
        m = getattr(m, p)
    return m


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


def class_canonical_name(depth):
    frame = sys._getframe(depth)
    module = frame.f_locals['__module__']
    class_name = frame.f_code.co_name
    return '.'.join([module, class_name])


def inside_class_definition(depth):
    frame = sys._getframe(depth)
    locals = frame.f_locals
    # Try to make sure we were called from a class def. In 2.2.0 we can't
    # check for __module__ since it doesn't seem to be added to the locals
    # until later on.  (Copied From zope.interfaces.declartion._implements)
    if ((locals is frame.f_globals)
        or (('__module__' not in locals)
            and sys.version_info[:3] > (2, 2, 0))):
        return False
    return True


def formatted_function_name(function):
    if hasattr(function, 'original_func'):
        function = function.original_func
    argspec = inspect.getargspec(function)
    defaults = argspec.defaults and list(argspec.defaults) or list()

    if argspec.args and argspec.args[0] == 'self':
        argspec.args.pop(0)
    if argspec.args and argspec.args[0] == 'state':
        argspec.args.pop(0)

    args = argspec.args or list()
    display_args = [x if len(defaults) < -index \
                    else "%s=%s" % (x, defaults[index])
                    for x, index in zip(args, range(-len(args), 0, 1))]
    if argspec.varargs:
        display_args += ['*%s' % (argspec.varargs)]
    if argspec.keywords:
        display_args += ['**%s' % (argspec.keywords)]

    text = "%s(" % (function.__name__, )
    text += ', '.join(display_args)
    text += ')'
    return text


### Private Methods ###


def _canonical_type(obj):
    return obj.__module__ + "." + obj.__name__


def _canonical_none(obj):
    return None


def _canonical_method(obj):
    return _canonical_type(obj.im_class) + "." + obj.__name__


def _canonical_builtin(obj):
    return "__builtin__." + obj.__name__
