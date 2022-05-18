"""Serialization helpers."""

from __future__ import annotations

import weakref
from typing import Callable, Dict, MutableMapping

from yahp.hparams import Hparams

_initialized_object_to_hparams_instance: MutableMapping[object, Hparams] = weakref.WeakKeyDictionary()
_object_registry_key_tracker: MutableMapping[int, MutableMapping[object, str]] = {}

__all__ = ['serialize', 'register_hparams_for_instance']


def serialize(x: object):
    """Serialize ``x`` to a dictionary if possible.

    Args:
        x (object): Any object. If it is an instance of :class:`.Hparams` or was created via YAHP,
            then it will be serialized to a dictionary. Otherwise, it will be serialized to a string.

    Returns:
        The serialization of ``x``, either as a dictionary or as a string.
    """
    if not isinstance(x, Hparams):
        # See if yahp knows the underlying hparams class
        try:
            hparams_instance = _initialized_object_to_hparams_instance[x]
        except (TypeError, KeyError):
            # TypeError is raised if x is not hashable
            # KeyError is raised if it does not exist.
            # Impossible to convert a class back into its hparams
            # Best that can be done is use the string representation
            return str(x)
        else:
            return hparams_instance.to_dict()
    return x.to_dict()


def get_key_for_instance_and_registry(instance: object, registry: Dict[str, Callable]):
    try:
        return _object_registry_key_tracker[id(registry)][instance]
    except (KeyError, TypeError):
        # TypeError is raised if x is not hashable
        # KeyError is raised if it does not exist.
        return None


def register_hparams_for_instance(instance: object, hparams: Hparams):
    """Register the ``hparams`` for ``instance``.

    This function associates the original hparams class for an instance, so it
    is possible to serialize the object to its YAML representation
    via :func:`.serialize`.

    Args:
        instance (object): The instance.
        hparams (Hparams): The hparams.
    """
    try:
        _initialized_object_to_hparams_instance[instance] = hparams
    except TypeError:
        # some types, such as dataclasses, are not hashable
        # ignore it
        pass


def register_hparams_registry_key_for_instance(instance: object, registry: Dict[str, Callable], key: str):
    """Register the ``key`` in the ``hparams_registry`` for ``instance``.

    This function associates the key in an hparams registry for an instance, so it
    is possible to serialize the object to its YAML representation
    via :func:`.serialize`.

    Args:
        instance (object): The instance.
        registry (Dict[str, Dict[str, Callable]]): The registry.
        key (str): The key.
    """
    if id(registry) not in _object_registry_key_tracker:
        _object_registry_key_tracker[id(registry)] = weakref.WeakKeyDictionary()
    try:
        _object_registry_key_tracker[id(registry)][instance] = key
    except TypeError:
        # some types, such as dataclasses, are not hashable
        # ignore it
        pass
