# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

import logging
from dataclasses import MISSING, field
from typing import Any, Callable, overload

logger = logging.getLogger(__name__)


@overload
def required(doc: str) -> Any:
    ...


@overload
def required(doc: str, *, template_default: Any) -> Any:
    ...


def required(doc: str, *, template_default=MISSING):
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


def optional(doc: str, *, default=MISSING, default_factory=MISSING):
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
        raise ValueError("default or default_factory must be specified")
    return field(  # type: ignore
        metadata={
            'doc': doc,
        },
        default=default,
        default_factory=default_factory,
    )
