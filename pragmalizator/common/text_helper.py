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
import operator
import difflib
import re

from pragmalizator.common import reflect


class Table(object):

    def __init__(self, fields, lengths):
        self.fields = fields
        self.lengths = lengths

    def render(self, iterator):
        result = "".join(
            [x.ljust(length) for x, length in zip(self.fields, self.lengths)])
        result = [result, "^" * len(result)]
        for record in iterator:
            splited = map(self._split_on_newline, record)
            while any(splited):
                line = [self._pop(x) for x in splited]
                formated = [val.ljust(length)
                            for val, length in zip(line, self.lengths)]
                result += ["".join(formated)]
        return '\n'.join(result)

    def _split_on_newline(self, value):
        value = str(value)
        lines = value.split('\n')
        return lines

    def _pop(self, llist):
        if llist:
            return llist.pop(0)
        else:
            return ""


def format_block(block):
    '''
    Format the given block of text, trimming leading/trailing
    empty lines and any leading whitespace that is common to all lines.
    The purpose is to let us list a code block as a multiline,
    triple-quoted Python string, taking care of indentation concerns.
    '''
    # separate block into lines
    lines = str(block).split('\n')
    # remove leading/trailing empty lines
    while lines and not lines[0]:
        del lines[0]
    while lines and not lines[-1]:
        del lines[-1]
    # look at first line to see how much indentation to trim
    ws = re.match(r'\s*', lines[0]).group(0)
    if ws:
        lines = map(lambda x: x.replace(ws, '', 1), lines)
    # remove leading/trailing blank lines (after leading ws removal)
    # we do this again in case there were pure-whitespace lines
    while lines and not lines[0]:
        del lines[0]
    while lines and not lines[-1]:
        del lines[-1]
    return '\n'.join(lines) + '\n'


def extract_diff(str1, str2):
    result = []
    matches = difflib.SequenceMatcher(None, str1, str2)
    i = iter(matches.get_matching_blocks())
    la, lb, ls = i.next()
    if la or lb:
        result.append((str1[0:la], str2[0:lb]))
    la += ls
    lb += ls
    for a, b, s in i:
        a, b
        if s:
            result.append((str1[la:a], str2[lb:b]))
            la, lb = a + s, b + s
    if len(str1) > la or len(str2) > lb:
        result.append((str1[la:], str2[lb:]))
    return result


def format_diff(str1, str2, header="\n", first_header=""):
    sep = first_header
    result = ""
    for a, b in extract_diff(str1, str2):
        result += sep + "Exp '%s'" % a
        sep = header
        result += sep + "Got '%s'" % b
    return result


def format_args(*args, **kwargs):
    return ", ".join([repr(a) for a in args]
                     + ["%r=%r" % i for i in kwargs.iteritems()])


def format_call(callback, *args, **kwargs):
    return "%s(%s)" % (reflect.canonical_name(callback),
                       format_args(*args, **kwargs))
