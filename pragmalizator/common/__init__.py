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
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4


def first(iterator):
    '''
    Returns first element from the operator or None.

    @param iterator: Iterable.
    '''
    try:
        return next(iterator)
    except StopIteration:
        return None


def deep_compare(expected, value):

    def compare_value(v1, v2, path):
        if v1 == v2:
            return

        if isinstance(v1, (list, tuple)):
            return compare_iter(v1, v2, path)
        if isinstance(v1, dict):
            return compare_dict(v1, v2, path)
        return compare_object(v1, v2, path)

    def compare_iter(v1, v2, path):
        if not isinstance(v2, (list, tuple)):
            msg = ("expected list or tuple and got %s"
                   % (type(v2).__name__, ))
            return path, msg

        if len(v1) != len(v2):
            msg = "Expected %d item(s) and got %d" % (len(v1), len(v2))
            return path, msg

        i = 0
        a = iter(v1)
        b = iter(v2)
        try:
            while True:
                new_path = path + "[%s]" % i
                i += 1
                v1 = a.next()
                v2 = b.next()
                result = compare_value(v1, v2, new_path)
                if result:
                    return result
        except StopIteration:
            return path, "Lists or tuples do not compare equal"

    def compare_dict(v1, v2, path):
        if not isinstance(v2, dict):
            msg = ("expected dict and got %s"
                   % (type(v2).__name__, ))
            return path, msg

        if len(v1) != len(v2):
            msg = "Expected %d item(s) and got %d" % (len(v1), len(v2))
            return path, msg

        for k in v1:
            new_path = (path if path else "value") + "[%r]" % (k, )
            a = v1[k]
            if k not in v2:
                return new_path, "key not found"
            b = v2[k]
            result = compare_value(a, b, new_path)
            if result:
                return result

        return path, "Dictionaries do not compare equal"

    def compare_object(v1, v2, path):
        basic_types = (int, float, long, bool, str, unicode)
        if isinstance(v1, basic_types) or isinstance(v2, basic_types):
            if not isinstance(v2, type(v1)):
                msg = ("expected %s and got %s"
                       % (type(v1).__name__, type(v2).__name__))
                return path, msg
            else:
                msg = ("expected %s and got %s" % (v1, v2))
                return path, msg


        d1 = v1.__dict__
        d2 = v2.__dict__

        if len(d1) != len(d2):
            msg = ("Expected %d attribute(s) and got %d"
                   % (len(d1), len(d2)))
            return path, msg

        for k in d1:
            # Simplistic black list
            if k in ["medium", "agent"]:
                continue
            new_path = path + ("." if path else "") + "%s" % (k, )
            a = d1[k]
            if k not in d2:
                return new_path, "attribute not found"
            b = d2[k]
            result = compare_value(a, b, new_path)
            if result:
                return result

        return path, ("Instances %s and %s do not compare equal"
                      % (type(v1).__name__, type(v2).__name__))

    return compare_value(expected, value, "")
