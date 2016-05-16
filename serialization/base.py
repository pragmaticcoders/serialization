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

import copy
import enum
import sys
import types

from zope.interface.declarations import implementer
from zope.interface.interface import InterfaceClass

from six import with_metaclass

from future.utils import raise_
from past.types import long, unicode

from serialization import adapter, reflect, registry
from serialization.interface import ISerializable, Capabilities
from serialization.interface import ISnapshotable, IFreezer, IConverter
from serialization.interface import IRegistry, IExternalizer, IRestorator
from serialization.interface import IVersionAdapter


DEFAULT_CONVERTER_CAPS = set([Capabilities.int_values,
                              Capabilities.enum_values,
                              Capabilities.long_values,
                              Capabilities.float_values,
                              Capabilities.bytes_values,
                              Capabilities.unicode_values,
                              Capabilities.bool_values,
                              Capabilities.none_values,
                              Capabilities.tuple_values,
                              Capabilities.list_values,
                              Capabilities.set_values,
                              Capabilities.dict_values,
                              Capabilities.instance_values,
                              Capabilities.external_values,
                              Capabilities.type_values,
                              Capabilities.int_keys,
                              Capabilities.enum_keys,
                              Capabilities.long_keys,
                              Capabilities.float_keys,
                              Capabilities.str_keys,
                              Capabilities.unicode_keys,
                              Capabilities.bool_keys,
                              Capabilities.none_keys,
                              Capabilities.tuple_keys,
                              Capabilities.type_keys,
                              Capabilities.circular_references,
                              Capabilities.new_style_types,
                              Capabilities.meta_types])

DEFAULT_FREEZER_CAPS = DEFAULT_CONVERTER_CAPS \
    | set([Capabilities.builtin_values,
           Capabilities.function_values,
           Capabilities.method_values])

FREEZING_TAG_ATTRIBUTE = '__freezing_tag__'


def freeze_tag(name):
    """
    This is not using decorator.py because we need to access original function
    not the wrapper.
    """

    def decorator(func):
        setattr(func, FREEZING_TAG_ATTRIBUTE, name)
        return func

    return decorator


def register(restorator):
    """Register a class as a L{IRestorator} in the default global registry."""
    global _global_registry
    _global_registry.register(restorator)
    return restorator


def lookup(type_name):
    global _global_registry
    return _global_registry.lookup(type_name)


def get_registry():
    global _global_registry
    return _global_registry


@implementer(ISnapshotable)
class SnapshotableAdapter(object):
    """Make basic types a L{ISnapshotable} that return itself as snapshot."""

    def __init__(self, value):
        self.value = value

    ### ISnapshotable ###

    def snapshot(self):
        return self.value

basic_types = (int, bytes, unicode, float, type, bool, type(None))
for adapted in basic_types:
    adapter.register(adapted, ISnapshotable)


class MetaSnapshotable(type):

    def __init__(cls, name, bases, dct):
        if "type_name" not in dct:
            type_name = dct["__module__"] + "." + name
            setattr(cls, "type_name", type_name)
        super(MetaSnapshotable, cls).__init__(name, bases, dct)


@implementer(ISnapshotable)
class Snapshotable(with_metaclass(MetaSnapshotable, object)):
    """Simple L{ISnapshotable} that snapshot the instance attributes
    not starting by an underscore. If the class attribute type_name
    is not defined, the canonical name of the class is used."""

    referenceable = True

    ### ISnapshotable ###

    def snapshot(self):
        return dict([(k, v)
                     for k, v in self.__dict__.items()
                     if isinstance(k, str) and not k.startswith('_')])


@implementer(IVersionAdapter)
class MetaVersionAdapter(type):
    pass


@implementer(IVersionAdapter)
class VersionAdapter(with_metaclass(MetaVersionAdapter, object)):

    @classmethod
    def adapt_version(cls, snapshot, source_ver, target_ver):
        assert isinstance(source_ver, int)
        assert isinstance(target_ver, int)

        if source_ver < target_ver:
            template = "upgrade_to_%d"
            step = 1
        elif source_ver > target_ver:
            template = "downgrade_to_%d"
            step = -1
        else:
            # No adaption needed
            return snapshot

        for ver in range(source_ver + step, target_ver + step, step):
            method = getattr(cls, template % (ver, ), None)
            if method is not None:
                snapshot = method(snapshot)

        return snapshot

    @classmethod
    def store_version(cls, snapshot, version, version_atom):
        snapshot[version_atom] = version
        return snapshot


@implementer(IRestorator)
class MetaSerializable(MetaSnapshotable):
    pass


@implementer(ISerializable)
class Serializable(with_metaclass(MetaSerializable, Snapshotable)):
    """Simple L{ISerializable} that serialize and restore the full instance
    dictionary. If the class attribute type_name is not defined, the canonical
    name of the class is used."""

    type_name = None

    @classmethod
    def prepare(cls):
        return cls.__new__(cls)

    @classmethod
    def restore(cls, snapshot):
        instance = cls.prepare()
        instance.recover(snapshot)
        return instance

    def recover(self, snapshot):
        self.__dict__.update(snapshot)

    def restored(self):
        pass


@implementer(ISerializable)
class ImmutableSerializable(with_metaclass(MetaSerializable, Snapshotable)):
    """Simple immutable L{ISerializable} that serialize and restore
    the full instance dictionary. If the class attribute type_name
    is not defined, the canonical name of the class is used.
    Should be used for any serializable to be used as dictionary keys
    or set elements (the one providing __hash__)."""

    type_name = None

    @classmethod
    def prepare(cls):
        return None

    @classmethod
    def restore(cls, snapshot):
        instance = cls.__new__(cls)
        instance.recover(snapshot)
        return instance

    def recover(self, snapshot):
        self.__dict__.update(snapshot)

    def restored(self):
        pass


@implementer(IRegistry)
class Registry(registry.BaseRegistry):
    """Keep track of L{IRestorator}. Used by unserializers."""

    allow_blank_application = True
    verify_interface = IRestorator
    key_attribute = 'type_name'


@implementer(IExternalizer)
class Externalizer(object):
    """Simplistic implementation of L{IExternalizer}.
    WARNING, by default it uses id() for identifying instances,
    IT WILL NOT WORK IF THE INSTANCE GOT SERIALIZED/UNSERIALIZED
    because it's id() would change.."""

    def __init__(self):
        self._registry = {}  # {INSTANCE_ID: ISNTANCE}

    def add(self, instance):
        identifier = self.get_identifier(instance)
        self._registry[identifier] = instance

    def remove(self, instance):
        identifier = self.get_identifier(instance)
        del self._registry[identifier]

    def get_identifier(self, instance):
        if ISerializable.providedBy(instance):
            return instance.type_name, id(instance)
        return id(instance)

    ### IExternalizer ###

    def identify(self, instance):
        identifier = self.get_identifier(instance)
        if identifier in self._registry:
            return identifier
        return None

    def lookup(self, identifier):
        return self._registry.get(identifier, None)


def referenceable(method):
    """Used in BaseSerializer and its sub-classes to flatten referenceable
    values. Hide the reference handling from sub-classes.
    For example, to make strings referenceable in a sub-class only use
    this decorator with decorate flatten_str()."""

    def wrapper(self, value, *args):
        deref = self._prepare(value)
        if deref is not None:
            return deref
        packer, data = method(self, value, *args)
        return self._preserve(value, packer, data)

    return wrapper


@implementer(IFreezer, IConverter)
class Serializer(object):
    """Base class for serializers handling references.

    A post converter can be specified at construction time to be chained.
    If specified, the output of this converter will be passed to it
    and it's result will be returned instead. It could be used to format
    the serialized data to a binary stream.

    The serialization is done in two pass. First the structure is flattened
    to a list of list where the first element is None or a function used
    to pack the following values::

      "spam" -> [pack_bytes, "spam"]
      u"spam" -> [pack_unicode, u"spam"]
      42 -> [pack_int, 42]
      0.1 -> [pack_float, 0.1]
      2L -> [pack_long, 2L]
      (1, 2, 3) -> [pack_tuple, [1, 2, 3]]
      [1, 2, 3] -> [pack_list, [1, 2, 3]]
      set([1, 2, 3]) -> [pack_set, [1, 2, 3]]
      {1: 2, 3: 4} -> [pack_dict, [[pack_item, 1, 2], [pack_item, 3, 4]]]

    Then the lists are packed using the packing function if specified,
    starting from the leaf up to the root. For example, the following
    flattened structure::

      [pack_list, [[pack_int, 42], [pack_list, [pack_int, 18]]]]

    will be packed the following way::

      pack_list([pack_int(42), pack_list([pack_int(18)])])

    This class handle references by encapsulating values referenced multiple
    times inside a special "reference" value that use it's own packing
    function, and then use a special "dereference" value when later
    referenced::

      > a = [1]
      > b = [a, a]
      > serialize(b)
      [pack_list, [[pack_reference, [1, [pack_list, [pack_int, 1]]]],
      [pack_dereference, 1]]]

    Sub classes can override the packing functions used for each types.

    NOTE: because the flatten methods lookup table is done at class
    declaration time, overriding most of flatten_* method will not work.
    Only flatten_value, flatten_key, flatten_item, flatten_unknown,
    flatten_instance and flatten_frozen_instance can be overridden
    safely by subclasses. In case overriding other flatten_* method
    would be needed in the future, the lookup table initialization
    should be moved to the constructor and self should not be passed anymore
    as the first parameter because the function would be then bound.

    #FIXME: Add datetime types datetime, date, time and timedelta

    """

    pack_bytes = None
    pack_unicode = None
    pack_int = None
    pack_enum = None
    pack_long = None
    pack_float = None
    pack_bool = None
    pack_none = None
    pack_tuple = None
    pack_list = None
    pack_item = None
    pack_dict = None
    pack_type = None
    pack_type_name = None
    pack_instance = None
    pack_external = None
    pack_function = None
    pack_method = None
    pack_reference = None
    pack_dereference = None
    pack_frozen_instance = None
    pack_frozen_function = None
    pack_frozen_method = None
    pack_frozen_external = None

    def __init__(self, converter_caps=None, freezer_caps=None,
                 post_converter=None, externalizer=None, registry=None,
                 source_ver=None, target_ver=None, version_atom='.version'):
        global _global_registry
        assert ((source_ver is None) and (target_ver is None)) \
            or ((source_ver is not None) and (target_ver is not None))
        self.converter_capabilities = converter_caps or DEFAULT_CONVERTER_CAPS
        self.freezer_capabilities = freezer_caps or DEFAULT_FREEZER_CAPS
        self._post_converter = post_converter and IConverter(post_converter)
        self._externalizer = externalizer and IExternalizer(externalizer)
        self._registry = IRegistry(registry) if registry else _global_registry
        self._source_ver = source_ver
        self._target_ver = target_ver
        self._version_atom = version_atom
        self.reset()

    ### IFreezer ###

    def freeze(self, data):
        return self._convert(data, self.freezer_capabilities, True)

    ### IConverter ###

    def convert(self, data):
        return self._convert(data, self.converter_capabilities, False)

    ### protected ###

    def check_capabilities(self, cap, value, caps, freezing):
        if cap not in caps:
            kind = "Freezer" if freezing else "Serializer"
            raise ValueError("%s %s do not support %s: %r"
                             % (kind, reflect.canonical_name(self),
                                cap.name, value))

    def pack_value(self, data):
        if not isinstance(data, (list, tuple)):
            return data
        packer, value = data
        if isinstance(value, list):
            value = [self.pack_value(d) for d in value]
        if packer is not None:
            return packer(value)
        return value

    def flatten_value(self, value, caps, freezing):
        vtype = type(value)
        default = Serializer.flatten_unknown_value
        flattener = self._value_lookup.get(vtype, default)
        return flattener(self, value, caps, freezing)

    def flatten_key(self, key, caps, freezing):
        vtype = type(key)
        default = Serializer.flatten_unknown_key
        flattener = self._key_lookup.get(vtype, default)
        return flattener(self, key, caps, freezing)

    def post_convertion(self, data):
        if self._post_converter is not None:
            return self._post_converter.convert(data)
        return data

    def reset(self):
        self._freezing = False  # If we are freezing or serializing
        self._preserved = {}  # {OBJ_ID: FLATTENED_STRUCTURE}
        self._refids = {}  # {OBJ_ID: REFERENCE_ID}
        self._references = {}  # {OBJ_ID: REFERENCE_CONTAINER}
        self._memory = []
        self._refid = 0

    def flatten_unknown_value(self, value, caps, freezing):
        # Flatten enums
        if isinstance(value, enum.Enum):
            return self.flatten_enum_value(value, caps, freezing)

        # Flatten types and interfaces
        if isinstance(value, (type, InterfaceClass)):
            return self.flatten_type_value(value, caps, freezing)

        if self._externalizer is not None:
            extid = self._externalizer.identify(value)
            if extid is not None:
                return self.flatten_external(extid, caps, freezing)

        # Checks if value support the current required protocol
        # Could be ISnapshotable or ISerializable
        if freezing:

            try:
                snapshotable = ISnapshotable(value)
            except TypeError:
                raise_(
                    TypeError,
                    "Freezing of type %s values "
                    "not supported by %s. Value = %r."
                    % (type(value).__name__,
                       reflect.canonical_name(self), value),
                    sys.exc_info()[2]
                )

            return self.flatten_instance(snapshotable, caps, freezing)

        else:

            try:
                serializable = ISerializable(value)
            except TypeError:
                raise_(
                    TypeError,
                    "Serialization of type %s values "
                    "not supported by %s. Value = %r."
                    % (reflect.canonical_name(value),
                       reflect.canonical_name(self), value),
                    sys.exc_info()[2]
                )

            return self.flatten_instance(serializable, caps, freezing)

    def flatten_unknown_key(self, value, caps, freezing):
        # Flatten enums
        if isinstance(value, enum.Enum):
            return self.flatten_enum_key(value, caps, freezing)

        # Flatten types and interfaces
        if isinstance(value, (type, InterfaceClass)):
            return self.flatten_type_key(value, caps, freezing)

        # Instances are not supported in keys
        raise TypeError("Type %s keys not supported by serializer %s"
                        % (type(value).__name__,
                           reflect.canonical_name(self)))

    def flatten_item(self, value, caps, freezing):
        key, value = value
        return self.pack_item, [self.flatten_key(key, caps, freezing),
                                self.flatten_value(value, caps, freezing)]

    def flatten_bytes_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.bytes_values, value,
                                caps, freezing)
        return self.pack_bytes, value

    def flatten_unicode_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.unicode_values, value,
                                caps, freezing)
        return self.pack_unicode, value

    def flatten_int_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.int_values, value,
                                caps, freezing, )
        return self.pack_int, value

    def flatten_long_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.long_values, value,
                                caps, freezing)
        return self.pack_long, value

    def flatten_float_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.float_values, value,
                                caps, freezing)
        return self.pack_float, value

    def flatten_none_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.none_values, value,
                                caps, freezing)
        return self.pack_none, value

    def flatten_bool_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.bool_values, value,
                                caps, freezing)
        return self.pack_bool, value

    def flatten_enum_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.enum_values, value,
                                caps, freezing)
        return self.pack_enum, value

    def flatten_type_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.type_values, value,
                                caps, freezing)
        return self.pack_type, value

    def flatten_builtin_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.builtin_values, value,
                                caps, freezing)
        if freezing:
            return self.pack_frozen_builtin, value
        return self.pack_function, value

    def flatten_function_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.function_values, value,
                                caps, freezing)
        if freezing:
            return self.pack_frozen_function, value
        return self.pack_function, value

    def flatten_method_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.method_values, value,
                                caps, freezing)
        if freezing:
            if hasattr(value.__func__, FREEZING_TAG_ATTRIBUTE):
                tag = getattr(value.__func__, FREEZING_TAG_ATTRIBUTE)
                return self.flatten_value(tag, caps, freezing)
            return self.pack_frozen_method, value
        return self.pack_method, value

    @referenceable
    def flatten_tuple_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.tuple_values, value,
                                caps, freezing)
        return self.pack_tuple, [self.flatten_value(v, caps, freezing)
                                 for v in value]

    @referenceable
    def flatten_list_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.list_values, value,
                                caps, freezing)
        return self.pack_list, [self.flatten_value(v, caps, freezing)
                                for v in value]

    @referenceable
    def flatten_set_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.set_values, value,
                                caps, freezing)
        return self.pack_set, [self.flatten_value(v, caps, freezing)
                               for v in value]

    @referenceable
    def flatten_dict_value(self, value, caps, freezing):
        self.check_capabilities(Capabilities.dict_values, value,
                                caps, freezing)
        items = value.items()
        if freezing:
            # int(1) > str(2) rase error on PY3
            items = sorted(items, key=lambda i: str(i[0]))
        return self.pack_dict, [self.flatten_item(i, caps, freezing)
                                for i in items]

    def flatten_bytes_key(self, value, caps, freezing):
        self.check_capabilities(Capabilities.str_keys, value,
                                caps, freezing)
        return self.pack_bytes, value

    def flatten_unicode_key(self, value, caps, freezing):
        self.check_capabilities(Capabilities.unicode_keys, value,
                                caps, freezing)
        return self.pack_unicode, value

    def flatten_int_key(self, value, caps, freezing):
        self.check_capabilities(Capabilities.int_keys, value,
                                caps, freezing)
        return self.pack_int, value

    def flatten_long_key(self, value, caps, freezing):
        self.check_capabilities(Capabilities.long_keys, value,
                                caps, freezing)
        return self.pack_long, value

    def flatten_float_key(self, value, caps, freezing):
        self.check_capabilities(Capabilities.float_keys, value,
                                caps, freezing)
        return self.pack_float, value

    def flatten_none_key(self, value, caps, freezing):
        self.check_capabilities(Capabilities.none_keys, value,
                                caps, freezing)
        return self.pack_none, value

    def flatten_bool_key(self, value, caps, freezing):
        self.check_capabilities(Capabilities.bool_keys, value,
                                caps, freezing)
        return self.pack_bool, value

    def flatten_enum_key(self, value, caps, freezing):
        self.check_capabilities(Capabilities.enum_keys, value,
                                caps, freezing)
        return self.pack_enum, value

    def flatten_type_key(self, value, caps, freezing):
        self.check_capabilities(Capabilities.type_keys, value,
                                caps, freezing)
        return self.pack_type, value

    @referenceable
    def flatten_tuple_key(self, value, caps, freezing):
        self.check_capabilities(Capabilities.tuple_keys, value,
                                caps, freezing)
        return self.pack_tuple, [self.flatten_value(v, caps, freezing)
                                 for v in value]

    def flatten_instance(self, value, caps, freezing):
        self.check_capabilities(Capabilities.instance_values, value,
                                caps, freezing)

        referenceable = getattr(value, "referenceable", True)

        if referenceable:
            deref = self._prepare(value)
            if deref is not None:
                return deref

        snapshot = value.snapshot()

        if IVersionAdapter.providedBy(value):
            source = self.get_source_ver(value, snapshot)
            target = self.get_target_ver(value, snapshot)
            if target is not None:
                if target != source:
                    snapshot = value.adapt_version(snapshot, source, target)
                value.store_version(snapshot, target, self._version_atom)

        dump = self.flatten_value(snapshot, caps, freezing)

        if freezing:
            packer, data = self.pack_frozen_instance, [dump]
        else:
            packer, data = (self.pack_instance,
                            [[self.pack_type_name, value.type_name], dump])

        if referenceable:
            return self._preserve(value, packer, data)
        else:
            return packer, data

    def flatten_external(self, value, caps, freezing):
        self.check_capabilities(Capabilities.external_values, value,
                                caps, freezing)
        flatened = [self.flatten_value(value, caps, freezing)]
        if not freezing:
            return self.pack_external, flatened
        return self.pack_frozen_external, flatened

    ### lookup tables ###

    _value_lookup = {tuple: flatten_tuple_value,
                     list: flatten_list_value,
                     set: flatten_set_value,
                     dict: flatten_dict_value,
                     bytes: flatten_bytes_value,
                     unicode: flatten_unicode_value,
                     int: flatten_int_value,
                     long: flatten_long_value,
                     float: flatten_float_value,
                     bool: flatten_bool_value,
                     type(None): flatten_none_value,
                     types.FunctionType: flatten_function_value,
                     types.BuiltinFunctionType: flatten_builtin_value,
                     types.MethodType: flatten_method_value}

    _key_lookup = {tuple: flatten_tuple_key,
                   bytes: flatten_bytes_key,
                   unicode: flatten_unicode_key,
                   int: flatten_int_key,
                   long: flatten_long_key,
                   float: flatten_float_key,
                   bool: flatten_bool_key,
                   type(None): flatten_none_key}

    ### private ###

    def _convert(self, data, caps, freezing):
        try:
            # Flatten the value to the list-only format with packer function
            flattened = self.flatten_value(data, caps, freezing)
            # Pack all the value with there own packer functions
            packed = self.pack_value(flattened)
            # Post-convert the data if a convert was specified
            return self.post_convertion(packed)
        finally:
            # Reset the state to cleanup all references
            self.reset()

    def _next_refid(self):
        self._refid += 1
        return self._refid

    def _prepare(self, value):
        ident = id(value)
        # Check if already preserved
        if ident in self._preserved:
            # Already preserved so we should return a dereference
            if ident in self._refids:
                # Already referenced, just use the reference identifier
                refid = self._refids[ident]
            else:
                # First dereference, we should mutate the original value
                # to a reference using the preserved list
                reference = self._preserved[ident]
                # Copy the original value before mutating
                new_value = copy.copy(reference)
                # Get a new reference identifier
                refid = self._next_refid()
                # Mutate the preserved list
                reference[:] = self.pack_reference, [refid, new_value]
                # Remember the reference identifier for this value
                self._refids[ident] = refid
                # Keep the reference to be able to return it from _preserv()
                # in case of cycle references
                self._references[ident] = reference
                # Update the original to be able to update
                # the reference value in-place
                self._preserved[ident] = new_value

            # Return a dereference
            return [self.pack_dereference, refid]

        # Preserve the value container to be able to mutate it to a reference
        self._preserved[ident] = []
        return None

    def _preserve(self, value, packer, data):
        ident = id(value)
        # Keep a reference to the value to prevent it to be garbage-collected.
        # If it was, a different value with the same id could appear
        # and the reference system would be corrupted.
        self._memory.append(value)
        # Retrieve the value container
        container = self._preserved[ident]
        # Set the value in place, even if it has been referenced
        container[:] = packer, data
        # If the value has been referenced, return the reference
        if ident in self._references:
            return self._references[ident]
        # Otherwise return the value itself
        return container

    def get_target_ver(self, instance, snapshot):
        return self._target_ver

    def get_source_ver(self, instance, snapshot):
        return self._source_ver


class DelayPacking(Exception):
    """Exception raised when unpacking a dereference to an unknown
    reference. This allows to delay unpacking of mutable object
    containing dereferences."""


@implementer(IConverter)
class Unserializer(object):
    """Base class for unserializers. It handle delayed unpacking
    and instance restoration to resolve circular references.
    If no registry instance is specified when created, the default
    global registry will be used.

    A pre-converter can be specified at creation time, if so the
    data will be first converted by the given converter and then
    the result will be unserialized. Used to parse data before
    unserializing.
    """

    pass_through_types = ()

    def __init__(self, converter_caps=None, pre_converter=None,
                 registry=None, externalizer=None,
                 source_ver=None, target_ver=None):
        global _global_registry
        assert ((source_ver is None) and (target_ver is None)) \
            or ((source_ver is not None) and (target_ver is not None))
        self.converter_capabilities = converter_caps or DEFAULT_CONVERTER_CAPS
        self._pre_converter = pre_converter and IConverter(pre_converter)
        self._registry = IRegistry(registry) if registry else _global_registry
        self._externalizer = externalizer and IExternalizer(externalizer)
        self._source_ver = source_ver
        self._target_ver = target_ver
        self.reset()

    ### IConverter ###

    def convert(self, data):
        try:
            # Pre-convert the data if a convertor was specified
            converted = self.pre_convertion(data)
            # Unpack the first level of values
            unpacked = self.unpack_data(converted)
            # Continue unpacking level by level
            self.finish_unpacking()
            # Inform object that it has migrated if this is a case
            if (IVersionAdapter.providedBy(unpacked) and
                    self._migrated):
                unpacked.set_migrated()

            # Should be finished by now
            return unpacked
        finally:
            # Reset the state to cleanup all references
            self.reset()

    ### protected ###

    def pre_convertion(self, data):
        if self._pre_converter is not None:
            return self._pre_converter.convert(data)
        return data

    def reset(self):
        self._references = {}  # {REFERENCE_ID: (DATA_ID, OBJECT)}
        self._pending = []  # Pendings unpacking
        self._instances = []  # [(RESTORATOR, INSTANCE, SNAPSHOT, REFID)]
        self._delayed = 0  # If we are in a delayable unpacking
        # If some snapshot has been migrated between versions
        self._migrated = False

    def unpack_data(self, data):
        return self._unpack_data(data, None, None)

    def delayed_unpacking(self, container, fun, *args, **kwargs):
        """Should be used when unpacking mutable values.
        This allows circular references resolution by pausing serialization."""
        try:
            self._delayed += 1
            blob = self._begin()
            try:
                fun(*args, **kwargs)
                self._commit(blob)
                return container
            except DelayPacking:
                self._rollback(blob)
                continuation = (fun, args, kwargs)
                self._pending.append(continuation)
                return container
        finally:
            self._delayed -= 1

    def finish_unpacking(self):
        while self._pending:
            fun, args, kwargs = self._pending.pop(0)
            fun(*args, **kwargs)

        # Initialize delayed mutable instances in creation order
        for restorator, instance, snapshot, _refid in self._instances:
            if restorator is not None:
                # delayed mutable instances
                snapshot = self._adapt_snapshot(restorator, snapshot)
                instance.recover(snapshot)

        # Calls the instances post restoration callback in reversed order
        # in an intent to reduce the possibilities of instances relying
        # on there references being fully restored when called.
        # This should not be relied on anyway.
        for _, instance, _, _ in reversed(self._instances):
            restored_fun = getattr(instance, "restored", None)
            if restored_fun is not None:
                restored_fun()

    def restore_type(self, type_name):
        value = reflect.named_object(type_name)
        if issubclass(value, type):
            raise ValueError("type %r unserialized to something that "
                             "isn't a type: %r" % (type_name, value))
        return value

    def restore_external(self, data):
        if self._externalizer is None:
            raise ValueError("Got external reference %r but unserializer "
                             "do not have any IExternalizer")
        identifier = self.unpack_data(data)
        instance = self._externalizer.lookup(identifier)
        if instance is None:
            raise ValueError("No external reference found with identifier %r"
                             % (identifier, ))
        return instance

    def prepare_instance(self, type_name):
        restorator = self._lookup_restorator(type_name)
        # Prepare the instance for recovery
        instance = restorator.prepare()
        if instance is not None:
            return restorator, instance

    def restore_instance(self, type_name, data, refid=None,
                         restorator=None, instance=None):
        if restorator is None:
            restorator = self._lookup_restorator(type_name)

        if instance is None:
            # Prepare the instance for recovery
            instance = restorator.prepare()

        if instance is None:
            # Immutable type, we can't delay restoration
            snapshot = self.unpack_data(data)
            snapshot = self._adapt_snapshot(restorator, snapshot)
            instance = restorator.restore(snapshot)
            self._instances.append((None, instance, None, refid))

            return instance

        # Delay the instance restoration for later to handle circular refs
        return self.delayed_unpacking(instance,
                                      self._continue_restoring_instance,
                                      restorator, instance, data, refid)

    def restore_reference(self, refid, data):
        if refid in self._references:
            # This is because of DelayUnpacking exception, reference
            # can be registered multiple times
            data_id, value = self._references[refid]
            if data_id == id(data):
                return value
            raise ValueError("Multiple references found with "
                             "the same identifier: %s" % refid)
        value = self._unpack_data(data, refid, data)
        if refid not in self._references:
            # If not yet referenced
            self._references[refid] = (id(data), value)
        return value

    def restore_dereference(self, refid):
        if refid not in self._references:
            # Dereference to an unknown reference
            if self._delayed > 0:
                # If we unpacking can be delayed because we are unpacking
                # a mutable object just delay the unpacking for later
                raise DelayPacking()
            raise ValueError("Dereferencing of yet unknown reference: %s"
                             % refid)
        _data_id, value = self._references[refid]
        return value

    def unpack_unordered_values(self, values):
        """Unpack an unordered list of values taking DelayPacking
        exceptions into account to resolve circular references .
        Used to unpack set values when order is not guaranteed by
        the serializer. See unpack_unordered_pairs()."""

        values = list(values)  # To support iterators
        result = []

        # Try to unpack values more than one time to resolve cross references
        max_loop = 2
        while values and max_loop:
            next_values = []
            for value_data in values:
                blob = self._begin()
                try:
                    # try unpacking the value
                    value = self.unpack_data(value_data)
                    self._commit(blob)
                except DelayPacking:
                    self._rollback(blob)
                    # If it is delayed keep it for later
                    next_values.append(value_data)
                    continue
                result.append(value)
            values = next_values
            max_loop -= 1

        if values:
            # Not all items were resolved
            raise DelayPacking()

        return result

    def unpack_unordered_pairs(self, pairs):
        """Unpack an unordered list of value pairs taking DelayPacking
        exceptions into account to resolve circular references .
        Used to unpack dictionary items when the order is not guarennteed
        by the serializer. When item order change between packing
        and unpacking, references are not guaranteed to appear before
        dereferences anymore. So if unpacking an item fail because
        of unknown dereference, we must keep it aside, continue unpacking
        the other items and continue later."""

        items = [(False, k, v) for k, v in pairs]
        result = []

        # Try to unpack items more than one time to resolve cross references
        max_loop = 2
        while items and max_loop:
            next_items = []
            for key_unpacked, key_data, value_data in items:
                if key_unpacked:
                    key = key_data
                else:
                    blob = self._begin()
                    try:
                        # Try unpacking the key
                        key = self.unpack_data(key_data)
                        self._commit(blob)
                    except DelayPacking:
                        self._rollback(blob)
                        # If it is delayed keep it for later
                        next_items.append((False, key_data, value_data))
                        continue

                blob = self._begin()
                try:
                    # try unpacking the value
                    value = self.unpack_data(value_data)
                    self._commit(blob)
                except DelayPacking:
                    self._rollback(blob)
                    # If it is delayed keep it for later
                    next_items.append((True, key, value_data))
                    continue

                # Update the container with the unpacked value and key
                result.append((key, value))
            items = next_items
            max_loop -= 1

        if items:
            # Not all items were resolved
            raise DelayPacking()

        return result

    ### virtual ###

    def analyse_data(self, data):
        """Analyses the data provided and return a tuple containing
        the data type and a function to unpack it.
        The type can be None for immutable types, instances,
        reference and dereferences."""

    ### private ###

    def _begin(self):
        # Start a DelayPacking protected section
        blob = self._instances
        self._instances = []
        return blob

    def _rollback(self, blob):
        # We need to rollback after a DelayPacking has been raised
        # we only keep instances that has been referenced
        for instance in self._instances:
            refid = instance[3]
            if refid is not None:
                blob.append(instance)
        self._instances = blob

    def _commit(self, blob):
        # Commit after a DelayPacking protected section
        # Joining the instance lists
        blob.extend(self._instances)
        self._instances = blob

    def _lookup_restorator(self, type_name):
        # Lookup the registry for a IRestorator
        restorator = self._registry.lookup(type_name)
        if restorator is None:
            raise TypeError("Type %s not supported by unserializer %s"
                            % (type_name, reflect.canonical_name(self)))
        return restorator

    def _unpack_data(self, data, refid, refdata):
        # Just return pass-through types,
        # support sub-classed base types and metaclasses
        if set(type(data).__mro__) & self.pass_through_types:
            return data

        analysis = self.analyse_data(data)

        if analysis is not None:

            constructor, unpacker = analysis

            if constructor is None:
                # Immutable types
                return unpacker(self, data)

            if callable(constructor):
                # Unpack the mutable containers that provides constructor
                container = constructor()
                if container is not None:
                    if refid is not None:
                        self._references[refid] = (id(refdata), container)
                    return self.delayed_unpacking(container, unpacker,
                                                  self, container, data)

            else:
                # Instance type name
                prepared = self.prepare_instance(constructor)
                if prepared is None:
                    # Immutable instance
                    return unpacker(self, data, None, None, None)

                restorator, instance = prepared

                if refid is not None:
                    self._references[refid] = (id(refdata), instance)
                return self.delayed_unpacking(instance, unpacker, self, data,
                                              refid, restorator, instance)

        raise TypeError("Type %s not supported by unserializer %s"
                        % (type(data).__name__,
                           reflect.canonical_name(self)))

    def _continue_restoring_instance(self, restorator, instance, data, refid):
        snapshot = self.unpack_data(data)
        # Delay instance initialization to the end to be sure
        # all snapshots circular references have been resolved
        self._instances.append((restorator, instance, snapshot, refid))
        return instance

    def _adapt_snapshot(self, restorator, snapshot):
        try:
            adapter = IVersionAdapter(restorator)
        except TypeError:
            pass
        else:
            target = self.get_target_ver(restorator, snapshot)
            source = self.get_source_ver(restorator, snapshot)
            if target is not None and target != source:
                snapshot = adapter.adapt_version(snapshot, source, target)
        return snapshot

    def get_target_ver(self, restorator, snapshot):
        return self._target_ver

    def get_source_ver(self, restorator, snapshot):
        return self._source_ver


### private ###

_global_registry = Registry()
