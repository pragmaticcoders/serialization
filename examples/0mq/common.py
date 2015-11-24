# -*- coding: utf-8 -*-
from __future__ import absolute_import

import serialization
import operator

class StackError(Exception):
    pass


@serialization.register
class Stack(serialization.Serializable):

    def __init__(self, max_size=None):
        self.max_size = max_size
        self.items = []

    @property
    def empty(self):
        return self.items == []

    def push(self, item):
        if self.max_size is not None and (self.size > self.max_size):
            raise StackError("Max stack size was reached.")
        self.items.append(item)

    def pop(self):
        if not self.size:
            raise StackError("Stack is empty.")
        return self.items.pop()

    def peek(self):
        return self.items[len(self.items) - 1]

    def __str__(self):
        return str(self.items)

    @property
    def size(self):
        return len(self.items)


@serialization.register
class Stacker(serialization.Serializable):

    def __init__(self):
        self.stacks = []

    def add_stack(self, stack):
        self.stacks.append(stack)

    def sum(self):
        new_stack = Stack(self.stacks[0].size)
        for r in zip(*[s.items for s in self.stacks]):
            new_stack.push(sum(r))
        return new_stack
