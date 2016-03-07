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

from future.utils import PY3

from six import with_metaclass

from . import reflect

_CLASS_ANNOTATIONS_ATTR = "_class_annotations"
_ATTRIBUTE_INJECTIONS_ATTR = "_attribute_injections"
_ANNOTATIONS_PROCESSED = "_annotations_processed"


class AnnotationError(Exception):
    pass


class MetaAnnotable(type):

    def __init__(cls, name, bases, dct):
        klasses = list(reversed(cls.mro()))

        # Class Initialization
        method = getattr(cls, "__class__init__", None)
        if method is not None:
            method(name, bases, dct)

        # Attribute Injection
        for k in klasses:
            injections = k.__dict__.get(_ATTRIBUTE_INJECTIONS_ATTR, None)
            if injections is not None:
                for attr, value in injections:
                    setattr(k, attr, value)
                del injections[:]

        pending_annotations = list()
        # Class Annotations

        for k in klasses:
            if k.__dict__.get(_ANNOTATIONS_PROCESSED, False):
                continue
            is_annotable = issubclass(type(k), MetaAnnotable)
            annotations = k.__dict__.get(_CLASS_ANNOTATIONS_ATTR, list())
            if annotations or pending_annotations:
                if is_annotable:
                    to_process = pending_annotations + annotations
                    for name, methodName, args, kwargs in to_process:
                        method = getattr(cls, methodName, None)
                        if method is None:
                            raise AnnotationError(
                                "Bad annotation %s set on class "
                                "%s, method %s not found"
                                % (name, k, methodName))
                        method(*args, **kwargs)
                    pending_annotations = list()
                    setattr(k, _ANNOTATIONS_PROCESSED, True)
                else:
                    pending_annotations.extend(annotations)

        super(MetaAnnotable, cls).__init__(name, bases, dct)


class Annotable(with_metaclass(MetaAnnotable, object)):
    __slots__ = ()  # To support sub-classes without __dict__


def injectClassCallback(annotationName, depth, methodName, *args, **kwargs):
    """
    Inject an annotation for a class method to be called
    after class initialization without dealing with metaclass.

    depth parameter specify the stack depth from the class definition.
    """
    locals = reflect.class_locals(depth, annotationName)
    annotations = locals.get(_CLASS_ANNOTATIONS_ATTR, None)
    if annotations is None:
        annotations = list()
        locals[_CLASS_ANNOTATIONS_ATTR] = annotations
    annotation = (annotationName, methodName, args, kwargs)
    annotations.append(annotation)


def injectAttribute(annotationName, depth, attr, value):
    """
    Inject an attribute in a class from it's class frame.
    Use in class annnotation to create methods/properties dynamically
    at class creation time without dealing with metaclass.

    depth parameter specify the stack depth from the class definition.
    """
    locals = reflect.class_locals(depth, annotationName)
    injections = locals.get(_ATTRIBUTE_INJECTIONS_ATTR, None)
    if injections is None:
        injections = list()
        locals[_ATTRIBUTE_INJECTIONS_ATTR] = injections
    injections.append((attr, value))
