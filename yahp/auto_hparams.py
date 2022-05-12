# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

import abc
import dataclasses
import inspect
from typing import Callable, Generic, Type, TypeVar

import yahp.field
from yahp.hparams import Hparams
from yahp.utils.type_helpers import HparamsType

TObject = TypeVar('TObject')


@dataclasses.dataclass
class AutoInitializedHparams(Hparams, abc.ABC, Generic[TObject]):
    """Subclass of :class:`.Hparams` where :meth:`.initialize_object` will be invoked automatically
    when being created from serialized data or the CLI.

    Unlike the generic :class:`.Hparams`, :meth:`.initialize_object` must take no arguments
    (other than self), since it will be invoked automatically.
    """

    def initialize_object(self) -> TObject:
        return super().initialize_object()


def generate_hparams_cls(constructor: Callable, auto_initialize: bool = True) -> Type[Hparams]:
    """Generate a :class:`.Hparams` from the signature and docstring of a callable.

    Args:
        constructor (Callable): A function or class
        auto_initialize (bool, optional): Whether to auto-initialize the class when instantiating it from
            configuration.

    Returns:
        Type[Hparams]: A subclass of :class:`.Hparams` where :meth:`.Hparams.initialize_object()` returns
            invokes the ``constructor``.
    """
    # dynamically generate an hparams class from an init signature

    # Extract the fields from the init signature
    field_list = []
    sig = inspect.signature(constructor)

    for param_name, param in sig.parameters.items():
        # Attempt to parse the annotation to ensure it is valid
        HparamsType(param.annotation)
        field_list.append((param_name, param.annotation, yahp.field.auto(constructor, param_name)))

    if len(field_list) == 0:
        # This is pointless to store something in yaml if it takes no arguments
        # Instead, it's more likely a mistake (e.g. a type annotation helper)
        # that yahp cannot parse into
        raise TypeError(f'Type annotation {constructor} is not supported as it takes no arguments')

    # Build the hparams class dynamically

    hparams_cls = dataclasses.make_dataclass(
        cls_name=constructor.__name__ + 'Hparams',
        fields=field_list,
        bases=(AutoInitializedHparams if auto_initialize else Hparams,),
        namespace={
            # If there was a registry, bind it -- otherwise set it to None
            'hparams_registry':
                getattr(constructor, 'hparams_registry', None),

            # Set the initialize_object function to something that, when invoked, calls the
            # constructor
            'initialize_object':
                lambda self: constructor(**{f.name: getattr(self, f.name) for f in dataclasses.fields(self)}),
        },
    )
    assert issubclass(hparams_cls, Hparams)
    return hparams_cls


def ensure_hparams_cls(constructor: Callable) -> Type[Hparams]:
    """Ensure that ``constructor`` is an hparams class."""
    if isinstance(constructor, type) and issubclass(constructor, Hparams):
        return constructor
    else:
        return generate_hparams_cls(constructor, auto_initialize=True)
