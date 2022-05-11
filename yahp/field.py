# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

import inspect
import logging
from dataclasses import _MISSING_TYPE, MISSING, field
from typing import Any, Callable, Union, overload

import docstring_parser

logger = logging.getLogger(__name__)

__all__ = ['required', 'optional', 'auto']


@overload
def required(doc: str) -> Any:
    ...


@overload
def required(doc: str, *, template_default: Any) -> Any:
    ...


def required(doc: str, *, template_default: Any = MISSING):
    """
    A required field for a :class:`~yahp.hparams.Hparams`.

    Args:
        doc (str): A description for the field.
            This description is printed when yahp is invoked with the
            ``--help`` CLI flag, and it may be included in generated
            YAML templates.
        template_default: Default to use when generating a YAML template.
            If not specified, no default value is included.
    """
    return field(metadata={
        'doc': doc,
        'template_default': template_default,
    },)


@overload
def optional(doc: str, *, default: Any) -> Any:
    ...


@overload
def optional(doc: str, *, default_factory: Callable[[], Any]) -> Any:
    ...


def optional(doc: str, *, default: Any = MISSING, default_factory: Union[_MISSING_TYPE, Callable[[], Any]] = MISSING):
    """
    An optional field for a :class:`yahp.hparams.Hparams`.

    Args:
        doc (str): A description for the field.
            This description is printed when YAHP is invoked with the
            ``--help`` CLI flag, and it may be included in generated
            YAML templates.
        default:
            Default value for the field.
            Cannot be specified with ``default_factory``.
            Required if ``default_factory`` is omitted.
        default_factory (optional):
            A function that returns a default value for the field.
            Cannot be specified with ``default``.
            Required if ``default`` is omitted.
    """
    if default == MISSING and default_factory == MISSING:
        raise ValueError('default or default_factory must be specified')
    return field(  # type: ignore
        metadata={
            'doc': doc,
        },
        default=default,
        default_factory=default_factory,
    )


def auto(constructor: Callable, arg_name: str):
    """A field automatically inferred from the docstring and signature.

    This helper will automatically parse the docstring and signature of a class or function to determine
    the documentation entry and default value for a field.

    For example:

    .. testcode::

        import dataclasses
        import yahp as hp

        class Foo:
            '''Foo.

            Args:
                bar (str): Required parameter.
                baz (int, optional): Optional parameter.
            '''

            def __init__(self, bar: str, baz: int = 42):
                self.bar = bar
                self.baz = baz

        @dataclasses.dataclass
        class FooHparams(hp.Hparams):
            bar: str = hp.auto(Foo, 'bar')  # Equivalent to hp.required(doc='Required parameter.')
            baz: int = hp.auto(Foo, 'baz')  # Equivalent to hp.optional(doc='Optional parameter.', default=42)

    Args:
        cls (Callable): The class or function.
        arg_name (str): The argument name within the class or function signature and docstring.

    Returns:
        A yahp field.
    """
    sig = inspect.signature(constructor)
    parameter = sig.parameters[arg_name]

    # Extract the documentation from the docstring
    docstring = constructor.__doc__
    if type(constructor) == type and constructor.__init__.__doc__ is not None:
        # If `constructor` is a class, then the docstring may be under `__init__`
        docstring = constructor.__init__.__doc__

    if docstring is None:
        raise ValueError(f'{constructor.__name__} does not have a docstring')
    parsed_docstring = docstring_parser.parse(docstring)
    docstring_params = parsed_docstring.params
    doc = None
    for param in docstring_params:
        if param.arg_name == arg_name:
            doc = param.description
    if doc is None:
        raise ValueError(f'{constructor} does not contain a docstring entry ')

    if parameter.default == inspect.Parameter.empty:
        return required(doc)
    else:
        return optional(doc, default=parameter.default)
