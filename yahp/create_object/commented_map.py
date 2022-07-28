# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

from dataclasses import MISSING, fields
from enum import Enum
from typing import TYPE_CHECKING, Callable, List, NamedTuple, Optional, Type, get_type_hints

import yahp as hp
from yahp.create_object.create_object import ensure_hparams_cls
from yahp.utils.interactive import query_with_options
from yahp.utils.iter_helpers import ensure_tuple, list_to_deduplicated_dict
from yahp.utils.type_helpers import HparamsType, get_default_value, is_field_required, safe_issubclass

if TYPE_CHECKING:
    from yahp.types import JSON, HparamsField

try:
    from ruamel_yaml import YAML  # type: ignore
    from ruamel_yaml.comments import CommentedMap, CommentedSeq  # type: ignore
except ImportError as _:
    from ruamel.yaml import YAML  # type: ignore
    from ruamel.yaml.comments import CommentedMap, CommentedSeq  # type: ignore


def _to_json_primitive(val: HparamsField) -> JSON:
    if isinstance(val, Enum):
        return val.name
    if val is None or isinstance(val, (str, float, int, dict)):
        # if dict, assuming already a json dict
        return val
    if isinstance(val, list):
        return [_to_json_primitive(x) for x in val]
    raise TypeError(f'Cannot convert value of type {type(val)} into a JSON primitive')


def _add_commenting(
    cm: CommentedMap,
    comment_key: str,
    eol_comment: str,
    typing_column: int,
    choices: Optional[List[str]] = None,
) -> None:
    if choices:
        eol_comment = f"{eol_comment} Options: {', '.join(choices)}."
    if typing_column + len(eol_comment) <= 120:
        cm.yaml_add_eol_comment(eol_comment, key=comment_key, column=typing_column)
    else:
        cm.yaml_set_comment_before_after_key(key=comment_key, before=eol_comment)
    cm.fa.set_block_style()


class CMOptions(NamedTuple):
    add_docs: bool
    typing_column: int
    interactive: bool


def _process_abstract_hparams(hparams: Type[hp.Hparams], path_with_fname: List[str], is_list: bool, options: CMOptions):
    """Generate a template for an abstract :class:`~yahp.hparams.Hparams`.

    If in interactive mode (as specified in ``options``), then a CLI prompt is used to determine which
    concrete subclass should be enumerated. Otherwise, all are dumped.

    Args:
        hparams (Type[hp.Hparams]):
            The parent of the abstract :class:`~yahp.hparams.Hparams` object.
        path_with_fname (List[str]):
            The path from the root :class:`~yahp.hparams.Hparams` to the abstract field.
        is_list (bool): Whether the abstract field is a list.
        options (CMOptions): CMOptions from :meth:`to_commented_map`.

    Returns:
        The generated template for the field, as a
        :class:`~ruamel.yaml.comments.CommentedSeq` if ``is_list``,
        otherwise, a :class:`~ruamel.yaml.comments.CommentedMap``
    """
    field_name = path_with_fname[-1]
    if hparams.hparams_registry is None:
        raise ValueError((
            f'{hparams.__name__}.{path_with_fname[-1]} is abstract, but {hparams.__name__} does not have an '
            f'hparams_registry dictionary. To fix, set {hparams.__name__}.hparams_registry to '
            'a registry dictionary. See '
            'https://docs.mosaicml.com/projects/yahp/en/stable/api_ref/hparams.html#yahp.hparams.Hparams.hparams_registry'
            ' for additional information.'))
    possible_sub_hparams = hparams.hparams_registry[field_name]
    possible_keys = list(possible_sub_hparams.keys())
    if options.interactive:
        leave_blank_option = '(Leave Blank)'
        dump_all_option = '(Dump all)'
        name = f"Field {'.'.join(path_with_fname)}:"
        if is_list:
            interactive_response = query_with_options(
                name=name,
                options=[leave_blank_option] + possible_keys + [dump_all_option],
                default_response=dump_all_option,
                multiple_ok=True,
            )
            if leave_blank_option in interactive_response:
                possible_keys = []
            elif dump_all_option not in interactive_response:
                possible_keys = interactive_response
        else:
            interactive_response = query_with_options(
                name=name,
                options=possible_keys + [dump_all_option],
                default_response=dump_all_option,
                multiple_ok=False,
            )
            if dump_all_option != interactive_response:
                possible_keys = [interactive_response]

    # filter possible_sub_hparams to those in possible_keys
    possible_sub_hparams = {k: v for (k, v) in possible_sub_hparams.items() if k in possible_keys}

    sub_hparams = CommentedMap()
    for sub_key, sub_type in possible_sub_hparams.items():
        sub_map = to_commented_map(
            constructor=sub_type,
            path=list(path_with_fname) + [sub_key],
            options=options,
        )

        sub_hparams[sub_key] = sub_map
        if options.add_docs:
            _add_commenting(sub_hparams,
                            comment_key=sub_key,
                            eol_comment=sub_type.__name__,
                            typing_column=options.typing_column)
    return sub_hparams


def to_commented_map(
    constructor: Callable,
    options: CMOptions,
    path: List[str],
) -> YAML:
    """Converts a Hparams class into a CommentedMap YAML template.

    .. note::
        This function should not be called directly.
        Instead, use :meth:`~yahp.hparams.Hparams.dump` or
        :meth:`~yahp.hparams.Hparams.dumps`.

    Args:
        cls (Type[hp.Hparams]): The class to geneate into a template
        options (CMOptions): Options for genearting the CommentedMap
        path (List[str]): Path to ``cls`` from the root.

    Returns:
        YAML: YAML template for ``cls``.
    """
    # TODO(averylamp) accept existing fields to create a new template from an existing one

    # Convert the class to an hparams class if a constructor was passed in
    cls = ensure_hparams_cls(constructor)
    output = CommentedMap()
    field_types = get_type_hints(cls)
    for f in fields(cls):
        if not f.init:
            continue
        path_with_fname = list(path) + [f.name]
        ftype = HparamsType(field_types[f.name])
        helptext = f.metadata.get('doc')
        helptext_suffix = f' Description: {helptext}.' if helptext is not None else ''
        required = is_field_required(f)
        default = get_default_value(f)
        default_suffix = ''
        optional_prefix = ' (Required)'
        if not required:
            optional_prefix = ' (Optional)'
            if default is None or safe_issubclass(default, (int, float, str, Enum)):
                default_suffix = f' Defaults to {default}.'
            elif safe_issubclass(default, hp.Hparams):
                default_suffix = f' Defaults to {type(default).__name__}.'
            # Don't print the default, it's too big
        if default == MISSING and 'template_default' in f.metadata:
            default = f.metadata['template_default']
        choices = []

        # The hparams type could be a primitive, enum, hparams class, custom object, or a list

        if not ftype.is_recursive:
            if default != MISSING:
                output[f.name] = _to_json_primitive(default)
            elif ftype.is_list:
                output[f.name] = CommentedSeq()
                if ftype.is_enum:
                    assert issubclass(ftype.type, Enum)
                    # If an enum list, then put all enum options in the list
                    output[f.name].extend([x.name for x in ftype.type])
            else:
                output[f.name] = None
        # it's a dataclass, or list of dataclasses
        elif cls.hparams_registry is None or f.name not in cls.hparams_registry:
            # non-abstract hparams
            if default is None:
                output[f.name] = None
            else:
                if default == MISSING:
                    # TODO(ravi): Repsect the allow_recursion flag
                    output[f.name] = [(to_commented_map(
                        constructor=ftype.type,
                        path=path_with_fname,
                        options=options,
                    ))]
                else:
                    output[f.name] = [x.to_dict() for x in ensure_tuple(default)]
                if not ftype.is_list:
                    output[f.name] = output[f.name][0]
                else:
                    output[f.name] = output[f.name]
        else:
            inverted_hparams = {v: k for (k, v) in cls.hparams_registry[f.name].items()}
            choices = [x.__name__ for x in cls.hparams_registry[f.name].values()]
            if default is None:
                output[f.name] = None
            elif default == MISSING:
                output[f.name] = _process_abstract_hparams(cls, path_with_fname, ftype.is_list, options)
            else:
                if ftype.is_list:
                    output[f.name] = list_to_deduplicated_dict([{
                        inverted_hparams[type(x)]: x.to_dict() if isinstance(x, hp.Hparams) else {}
                    } for x in ensure_tuple(default)])
                else:
                    output[f.name] = {
                        inverted_hparams[type(default)]: default.to_dict() if isinstance(default, hp.Hparams) else {},
                    }
        if options.add_docs:
            _add_commenting(cm=output,
                            comment_key=f.name,
                            eol_comment=f'{str(ftype): >20}{optional_prefix}.{helptext_suffix}{default_suffix}',
                            typing_column=options.typing_column,
                            choices=choices)
    return output
