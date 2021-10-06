from __future__ import annotations

import functools
from dataclasses import MISSING, fields
from enum import Enum
from typing import NamedTuple, Sequence, Type, get_type_hints

import yahp as hp
from yahp.interactive import query_multiple_options, query_singular_option
from yahp.type_helpers import HparamsType, get_default_value, is_field_required
from yahp.types import JSON, THparams
from yahp.utils import ensure_tuple

try:
    from ruamel_yaml import YAML  # type: ignore
    from ruamel_yaml.comments import CommentedMap, CommentedSeq  # type: ignore
except ImportError as _:
    from ruamel.yaml import YAML  # type: ignore
    from ruamel.yaml.comments import CommentedMap, CommentedSeq  # type: ignore


def _to_json_primitive(val: THparams) -> JSON:
    if isinstance(val, Enum):
        return val.name
    if val is None or isinstance(val, (str, float, int, dict)):
        # if dict, assuming already a json dict
        return val
    if isinstance(val, list):
        return [_to_json_primitive(x) for x in val]
    raise TypeError(f"Cannot convert value of type {type(val)} into a JSON primitive")


def _add_commenting(
        cm: CommentedMap,
        comment_helptext: bool,
        comment_key: str,
        eol_comment: str,
        typing_column: int,
        choices: Sequence[str] = tuple(),
        helptext: str = "",
) -> None:
    if comment_helptext:
        eol_comment = f"{helptext}: {eol_comment}"
        cm.yaml_set_comment_before_after_key(key=comment_key, before=eol_comment)
    if typing_column > 0:
        if choices:
            eol_comment = f"{eol_comment}. Choices: {', '.join(choices)}"
        if typing_column + len(eol_comment) <= 120:
            cm.yaml_add_eol_comment(eol_comment, key=comment_key, column=typing_column)
        else:
            cm.yaml_set_comment_before_after_key(key=comment_key, before=eol_comment)


class CMOptions(NamedTuple):
    comment_helptext: bool = False
    typing_column: int = 45
    choice_option_column: int = 35
    interactive: bool = False


def _process_registry_entry(hparams: Type[hp.Hparams], field_name: str, is_list: bool, options: CMOptions):
    possible_sub_hparams = hparams.hparams_registry[field_name]
    possible_keys = list(possible_sub_hparams.keys())
    if options.interactive:
        default_option = "Dump all"
        input_text = f"Please select a(n) {field_name}"
        if is_list:
            selection_helptext = "Put a number or comma separated numbers to choose"
            pre_helptext = input_text + ". Chose one or multiple..."
            interactive_response = query_multiple_options(
                input_text=input_text,
                options=possible_keys + [default_option],
                default_response=default_option,
                pre_helptext=pre_helptext,
                helptext=selection_helptext,
            )
            if default_option not in interactive_response:
                possible_keys = interactive_response
        else:
            selection_helptext = "Put a number to choose"
            pre_helptext = input_text + ". Choose one only..."
            interactive_response = query_singular_option(
                input_text=input_text,
                options=possible_keys + [default_option],
                default_response=default_option,
                pre_helptext=pre_helptext,
                helptext=selection_helptext,
            )
            if default_option != interactive_response:
                possible_keys = [interactive_response]

    # filter possible_sub_hparams to those in possible_keys
    possible_sub_hparams = {k: v for (k, v) in possible_sub_hparams.items() if k in possible_keys}

    sub_hparams = CommentedSeq() if is_list else CommentedMap()
    for sub_key, sub_type in possible_sub_hparams.items():
        sub_map = to_commented_map(
            cls=sub_type,
            options=options,
        )
        if is_list:
            sub_item = CommentedMap()
            sub_item[sub_key] = sub_map
            sub_hparams.append(sub_item)
            _add_commenting(sub_item,
                            comment_helptext=False,
                            comment_key=sub_key,
                            eol_comment=sub_type.__name__,
                            typing_column=options.choice_option_column)
            continue
        sub_hparams[sub_key] = sub_map
        _add_commenting(sub_hparams,
                        comment_helptext=False,
                        comment_key=sub_key,
                        eol_comment=sub_type.__name__,
                        typing_column=options.choice_option_column)
    return sub_hparams


def to_commented_map(
    cls: Type[hp.Hparams],
    options: CMOptions,
) -> YAML:
    output = CommentedMap()
    field_types = get_type_hints(cls)
    for f in fields(cls):
        ftype = HparamsType(field_types[f.name])
        helptext = f.metadata.get("doc", "")
        required = is_field_required(f)
        default = get_default_value(f)
        if default == MISSING and "template_default" in f.metadata:
            default = f.metadata["template_default"]
        add_commenting = functools.partial(
            _add_commenting,
            cm=output,
            comment_helptext=False,
            comment_key=f.name,
            eol_comment=f"{'required' if required else 'optional'}: {str(ftype)}",
            typing_column=options.typing_column,
            helptext=helptext,
        )
        if not ftype.is_hparams_dataclass:
            if default != MISSING:
                output[f.name] = _to_json_primitive(default)
                add_commenting()
                continue

            if ftype.is_list:
                output[f.name] = CommentedSeq()
                add_commenting()
                if ftype.is_enum:
                    # If an enum list, then put all enum options in the list
                    output[f.name].extend([x.name for x in ftype.type])
                continue
            output[f.name] = None
            add_commenting()
            continue
        # it's a dataclass, or list of dataclasses
        if default is None:
            # note that None means actually None, not MISSING!
            output[f.name] = None
            add_commenting()
            continue

        if ftype.is_list:
            # list of dataclasses
            if f.name not in cls.hparams_registry:
                # list of concrete dataclasses
                if default is None:
                    output[f.name] = None
                elif default == MISSING:
                    output[f.name] = [(to_commented_map(
                        cls=ftype.type,
                        options=options,
                    ))]
                else:
                    output[f.name] = [x.to_dict() for x in ensure_tuple(default)]
                add_commenting()
                continue
            else:
                # list of abstract hparams
                concrete_class_names = [x.__name__ for x in cls.hparams_registry[f.name].values()]
                if default is None:
                    output[f.name] = None
                elif default == MISSING:
                    output[f.name] = _process_registry_entry(cls, f.name, ftype.is_list, options)
                else:
                    inverted_hparams = {v: k for (k, v) in cls.hparams_registry[f.name].items()}
                    output[f.name] = [{inverted_hparams[type(x)]: x.to_dict()} for x in ensure_tuple(default)]
                add_commenting(choices=concrete_class_names)
                continue
        if f.name not in cls.hparams_registry:
            # non-abstract, singleton hparams
            if default is None:
                output[f.name] = None
            elif default == MISSING:
                output[f.name] = to_commented_map(cls=ftype.type, options=options)
            else:
                output[f.name] = default.to_dict()
                add_commenting()
            add_commenting()
            continue
        # abstract, singleton hparams
        concrete_class_names = [x.__name__ for x in cls.hparams_registry[f.name].values()]
        if default is None:
            output[f.name] = None
        elif default == MISSING:
            output[f.name] = _process_registry_entry(cls, f.name, ftype.is_list, options)
        else:
            inverted_hparams = {v: k for (k, v) in cls.hparams_registry[f.name].items()}
            output[f.name] = {inverted_hparams[type(default)]: default.to_dict()}
        add_commenting(choices=concrete_class_names)
    return output
