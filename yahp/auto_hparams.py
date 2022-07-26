# Copyright 2021 MosaicML. All Rights Reserved.

import dataclasses
import inspect
from typing import Any, Callable, Type, get_type_hints

import yahp.field
from yahp.hparams import Hparams
from yahp.utils.type_helpers import HparamsType

__all__ = [
    'generate_hparams_cls',
    'ensure_hparams_cls',
]


def generate_hparams_cls(constructor: Callable, ignore_docstring_errors: bool = False) -> Type[Hparams]:
    """Generate a :class:`.Hparams` from the signature and docstring of a callable.

    Args:
        constructor (Callable): A function or class
        auto_initialize (bool, optional): Whether to auto-initialize the class when instantiating it from
            configuration.
        ignore_docstring_errors (bool, optional): Whether to ignore any docstring errors.

    Returns:
        Type[Hparams]: A subclass of :class:`.Hparams` where :meth:`.Hparams.initialize_object()` returns
            invokes the ``constructor``.
    """
    # dynamically generate an hparams class from an init signature

    # Extract the fields from the init signature
    field_list = []

    type_hints = get_type_hints(constructor.__init__ if isinstance(constructor, type) else constructor)
    sig = inspect.signature(constructor)
    parameters = sig.parameters

    for param_name in parameters:
        # Using the `type_hints` dictionary to ensure that forward references are resolved
        # If it is untyped, resolve to 'Any'
        param_annotation = type_hints.get(param_name, Any)
        assert not isinstance(param_annotation, str), 'type hints must be resolved'
        # Attempt to parse the annotation to ensure it is valid
        try:
            HparamsType(param_annotation)
        except TypeError as e:
            raise TypeError(
                f'Type annotation {param_annotation} for field {constructor.__name__}.{param_name} is not supported'
            ) from e

        auto_field = yahp.field.auto(constructor, param_name, ignore_docstring_errors=ignore_docstring_errors)

        field_list.append((param_name, param_annotation, auto_field))

    # Build the hparams class dynamically

    hparams_cls = dataclasses.make_dataclass(
        cls_name=constructor.__name__ + 'Hparams',
        fields=field_list,
        bases=(Hparams,),
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
    """Ensure that ``constructor`` is a :class:`.Hparams` class.

    Args:
        constructor (Callable): A class, function, or existing :class:`.Hparams` class.
            If an existing :class:`.Hparams`, it will be returned as-is; otherwise
            :func:`generate_hparams_cls` will be used to dynamically create a
            :class:`.Hparams` from the docstring and signature.
    Returns:
        Type[Hparams]: A :class:`.Hparams` class.
    """
    if isinstance(constructor, type) and issubclass(constructor, Hparams):
        return constructor
    else:
        return generate_hparams_cls(constructor)
