from __future__ import absolute_import


class SerializeError(Exception):
    pass


class SerializeCompatError(SerializeError):
    pass


class SerializeRequirementError(SerializeError, ImportError):
    pass
