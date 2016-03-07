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
# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
from __future__ import absolute_import

from future.utils import PY3
from six import iterkeys

from serialization import annotate


class GoodDummy(annotate.Annotable):
    '''Reference for the following test.'''

    annotate.injectClassCallback("dummy", 2, "good_method")

    @classmethod
    def good_method(cls):
        pass


def accompany(accompaniment):
    '''Method decorator'''

    def decorator(method):

        def get_accompaniment(self, *args, **kwargs):
            #Create a method for the accompaniment
            return self.name + " wants " + accompaniment

        # Inject the new method in the class
        annotate.injectAttribute("accompany", 3,
                                 accompaniment, get_accompaniment)

        # Inject the original method with a new name
        annotate.injectAttribute("accompany", 3,
                                 "original_" + method.__name__, method)

        def wrapper(self, *args, **kwargs):
            #Wrapp a method call and add an accompaniment to its result
            result = method(self, *args, **kwargs)
            return result + " and " + accompaniment

        # Call the class to register the decorator
        annotate.injectClassCallback("accompany", 3, "_decorator",
                                     accompaniment, method, wrapper)

        return wrapper
    return decorator


def shop(animal, status):
    '''Class annotation. Create a getter method'''

    def getter(self):
        return self.name + " " + animal + " is " + status
    annotate.injectAttribute("shop", 3, "get_" + animal, getter)
    return status


class Annotated(annotate.Annotable):
    class_init = False
    obj_init = False

    accompaniments = {}

    # Annotations

    shop("parrot", "dead")
    shop("slug", "mute")

    @classmethod
    def __class__init__(cls, name, bases, dct):
        cls.class_init = True

    @classmethod
    def _decorator(cls, accompaniment, old, new):
        cls.accompaniments[accompaniment] = (old, new)

    def __init__(self, name):
        self.obj_init = True
        self.name = name

    @accompany("beans")
    def spam(self, kind):
        return self.name + " like " + kind + " spam"

    @accompany("eggs")
    def bacon(self, kind):
        return self.name + " like " + kind + " bacon"

try:
    bad_annotation_method_fail = False

    class BadDummy(annotate.Annotable):
        '''Reference for the following test.'''

        annotate.injectClassCallback("dummy", 2, "wrong_method")

        @classmethod
        def good_method(cls):
            pass
except annotate.AnnotationError:
    bad_annotation_method_fail = True


def mixin(fun):
    annotate.injectClassCallback("mixin", 3, "_register", fun)
    return fun


class MixinTestBase(annotate.Annotable):

    values = None

    @classmethod
    def __class__init__(cls, name, bases, dct):
        values = dict()
        for base in [cls] + list(bases):
            parent_values = getattr(base, "values", None)
            if parent_values:
                values.update(parent_values)
        cls.values = values

    @classmethod
    def _register(cls, value):
        if cls.values is None:
            cls.values = dict()
        assert value not in cls.values, "Values are: %r" % (cls.values, )
        cls.values[value] = cls

    @mixin
    def first_annotation(self):
        pass


class MixinTestMixin(object):

    @mixin
    def mixin_annotation(self):
        pass

    @mixin
    def overloaded_annotation(self):
        '''this is to test overloading annotated methods'''


class MixinTestDummy(MixinTestBase, MixinTestMixin):

    @mixin
    def second_annotation(self):
        pass

    @mixin
    def overloaded_annotation(self):
        '''this is to test overloading annotated methods'''


class TestAnnotation(object):

    def test_mix_in(self):
        assert (
            set(iterkeys(MixinTestBase.values)) ==
            set([_get_func(MixinTestBase.first_annotation)])
        )
        assert (
            set(iterkeys(MixinTestDummy.values)) ==
            set([
                _get_func(MixinTestBase.first_annotation),
                _get_func(MixinTestDummy.second_annotation),
                _get_func(MixinTestDummy.overloaded_annotation),
                _get_func(MixinTestMixin.mixin_annotation),
                _get_func(MixinTestMixin.overloaded_annotation),
            ])
        )

        # now check that the _register call has been done with correct cls
        # as the parameter
        assert not hasattr(MixinTestMixin, "values")

        def get_cls(fun):
            return MixinTestDummy.values.get(_get_func(fun))

        assert (
            MixinTestBase ==
            get_cls(MixinTestBase.first_annotation))
        assert (
            MixinTestDummy ==
            get_cls(MixinTestDummy.second_annotation))
        assert (
            MixinTestDummy ==
            get_cls(MixinTestDummy.overloaded_annotation))
        assert (
            MixinTestDummy ==
            get_cls(MixinTestMixin.overloaded_annotation))
        assert (
            MixinTestDummy ==
            get_cls(MixinTestMixin.mixin_annotation))

    def testMetaErrors(self):
        assert bad_annotation_method_fail

    def testInitialization(self):
        assert Annotated.class_init
        assert not Annotated.obj_init
        obj = Annotated("Monthy")
        assert obj.class_init
        assert obj.obj_init

    def testAnnotations(self):
        assert hasattr(Annotated, "get_parrot")
        assert hasattr(Annotated, "get_slug")
        obj = Annotated("Monthy")
        assert hasattr(obj, "get_parrot")
        assert hasattr(obj, "get_slug")
        assert "Monthy parrot is dead" == obj.get_parrot()
        assert "Monthy slug is mute" == obj.get_slug()

    def testDecorator(self):
        assert hasattr(Annotated, "spam")
        assert hasattr(Annotated, "bacon")
        assert hasattr(Annotated, "original_spam")
        assert hasattr(Annotated, "original_bacon")
        assert hasattr(Annotated, "beans")
        assert hasattr(Annotated, "eggs")

        assert "beans" in Annotated.accompaniments
        assert "eggs" in Annotated.accompaniments

        obj = Annotated("Monthy")

        assert "Monthy like a lot of spam and beans" == obj.spam("a lot of")
        assert "Monthy like so much bacon and eggs" == obj.bacon("so much")

        assert "Monthy like a lot of spam" == obj.original_spam("a lot of")
        assert "Monthy like so much bacon" == obj.original_bacon("so much")

        assert "Monthy wants beans" == obj.beans()
        assert "Monthy wants eggs" == obj.eggs()


def _get_func(f):
    if PY3:
        return f
    else:
        return f.__func__
