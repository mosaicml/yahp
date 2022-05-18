# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

import inspect
import logging
import warnings
from dataclasses import _MISSING_TYPE, MISSING, field
from typing import Any, Callable, Optional, TypeVar, Union, overload

import docstring_parser

logger = logging.getLogger(__name__)

__all__ = ['required', 'optional', 'auto']

TObject = TypeVar('TObject')


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
def optional(doc: str, *, default: TObject) -> TObject:
    ...


@overload
def optional(doc: str, *, default_factory: Callable[[], TObject]) -> TObject:
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


def _extract_doc_from_docstring(docstring: str, arg_name: str):
    # Extract the documentation from the docstring

    parsed_docstring = docstring_parser.parse(docstring)
    docstring_params = parsed_docstring.params
    doc = None
    for param in docstring_params:
        if param.arg_name == arg_name:
            doc = param.description
    if doc is None:
        raise ValueError(f'Argument {arg_name} is not in the docstring')
    return doc


def auto(constructor: Callable, arg_name: str, doc: Optional[str] = None, ignore_docstring_errors: bool = False):
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
        doc (str, optional): If provided, use this value for argparse documentation, instead of attempting
            to extract it from the docstring.
        ignore_docstring_errors (bool, optional): If False, ignore any errors from parsing the docstring.
            Useful if the ``constructor`` is in a third-party library.

    Returns:
        A yahp field.
    """
    sig = inspect.signature(constructor)
    try:
        parameter = sig.parameters[arg_name]
    except KeyError:
        raise ValueError(f'Constructor {constructor} does not have an argument named {arg_name}')

    if doc is None:
        docstring = constructor.__doc__
        if type(constructor) == type and constructor.__init__.__doc__ is not None:
            # If `constructor` is a class, then the docstring may be under `__init__`
            docstring = constructor.__init__.__doc__

        if docstring is None:
            msg = f'{constructor.__name__} has no docstring. Argument {arg_name} will be undocumented.'
            if ignore_docstring_errors:
                warnings.warn(msg)
            else:
                raise ValueError(msg)
            doc = arg_name
        else:
            try:
                doc = _extract_doc_from_docstring(docstring=docstring, arg_name=arg_name)
            except (docstring_parser.ParseError, ValueError) as e:
                msg = (f'Unable to extract docstring for argument {arg_name} from {constructor.__name__}. '
                       f'Argument {arg_name} will be undocumented.')
                if ignore_docstring_errors:
                    warnings.warn(f'{msg}: {e}')
                    doc = arg_name
                else:
                    raise ValueError(msg) from e

    assert doc is not None, 'doc was set above'
    if parameter.default == inspect.Parameter.empty:
        return required(doc)
    else:
        return optional(doc, default=parameter.default)
