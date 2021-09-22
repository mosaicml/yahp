from __future__ import annotations

from dataclasses import fields
from typing import Type, get_type_hints

import yahp as hp
from yahp import type_helpers
from yahp.interactive import list_options

try:
    from ruamel_yaml import YAML  # type: ignore
    from ruamel_yaml.comments import CommentedMap, CommentedSeq  # type: ignore
except ImportError as _:
    from ruamel.yaml import YAML  # type: ignore
    from ruamel.yaml.comments import CommentedMap, CommentedSeq  # type: ignore


def _to_commented_map(
    cls: Type[hp.Hparams],
    comment_helptext: bool = False,
    typing_column: int = 45,
    choice_option_column: int = 35,
    interactive: bool = False,
) -> YAML:
    output = CommentedMap()
    persisted_args = {
        "comment_helptext": comment_helptext,
        "typing_column": typing_column,
        "choice_option_column": choice_option_column,
        "interactive": interactive,
    }

    def add_commenting(cm: CommentedMap,
                       comment_key: str,
                       required_string: str,
                       type_string: str,
                       helptext: str = "") -> None:
        eol_comment = f"{required_string}: {type_string}"  # type: ignore
        if comment_helptext:
            eol_comment = f"{helptext}: {eol_comment}"  # type: ignore
            cm.yaml_set_comment_before_after_key(comment_key, before=eol_comment)
        if typing_column > 0:
            cm.yaml_add_eol_comment(eol_comment, key=comment_key, column=typing_column)

    field_types = get_type_hints(cls)
    for field in fields(cls):
        ftype = field_types[field.name]
        required, default = type_helpers._get_required_default_from_field(field=field)
        if required and field.metadata.get("template_default") is not None:
            default = field.metadata.get("template_default")
        required_string = "required" if required else "optional"
        type_name = type_helpers._get_type_name(ftype)
        helptext = field.metadata.get("doc", "")
        default_commenting_args = {
            "cm": output,
            "comment_key": field.name,
            "required_string": required_string,
            "type_string": type_name,
            "helptext": helptext,
        }

        if type_helpers._is_primitive_optional_type(ftype):
            output[field.name] = cls._to_json_primitive(default)
            add_commenting(**default_commenting_args)
        else:
            # a List, Hparams type, or Union involving these
            if field.name not in cls.hparams_registry:
                if type_helpers._is_json_dict(ftype):
                    output[field.name] = {}
                    add_commenting(**default_commenting_args)
                else:
                    real_ftype = type_helpers._get_real_ftype(ftype)
                    if type_helpers._is_list(ftype):
                        output[field.name] = CommentedSeq()
                        add_commenting(**default_commenting_args)
                        if default:
                            if type_helpers._is_enum_type(real_ftype):
                                # Take only enum values for default for reinstantiation
                                output[field.name].extend([x.value for x in default])
                            else:
                                output[field.name].extend(default)
                        if type_helpers._is_hparams_type(real_ftype):
                            assert issubclass(real_ftype, hp.Hparams)
                            output[field.name].append(_to_commented_map(
                                cls=real_ftype,
                                **persisted_args,
                            ))
                    elif type_helpers._is_hparams_type(real_ftype):
                        assert issubclass(real_ftype, hp.Hparams)
                        output[field.name] = _to_commented_map(
                            cls=real_ftype,
                            **persisted_args,
                        )
                    else:
                        raise TypeError(f"Invalid type: {real_ftype}")
            else:
                # It's a Chose One or a List
                possible_sub_hparams = cls.hparams_registry[field.name]
                possible_keys = [x for (x, y) in possible_sub_hparams]
                if len(possible_keys) == 1:
                    sub_hparams = CommentedMap()
                    sub_hparams_key, sub_hparams_type = list(possible_sub_hparams.items())[0]
                    if sub_hparams_key == field.name:
                        output[field.name] = _to_commented_map(
                            cls=sub_hparams_type,
                            **persisted_args,
                        )
                    else:
                        sub_hparams[sub_hparams_key] = _to_commented_map(
                            cls=sub_hparams_type,
                            **persisted_args,
                        )
                        output[field.name] = sub_hparams
                elif len(possible_keys) > 1:
                    is_list = type_helpers._is_list(ftype)
                    choice_type = "List" if is_list else "Choose one"
                    possible_string = ', '.join(possible_keys)
                    if interactive:
                        selection_helptext = "Put a number to choose" if not is_list else "Put a number or comma separated numbers to choose"
                        default_option = "Dump all"
                        input_text = f"Please select a(n) {field.name}"
                        pre_helptext = input_text + ". " + ("Chose one or multiple"
                                                            if is_list else "Choose one only") + "..."

                        interactive_response = list_options(
                            input_text=input_text,
                            options=possible_keys + [default_option],
                            default_response=default_option,
                            pre_helptext=pre_helptext,
                            multiple_ok=is_list,
                            helptext=selection_helptext,
                        )
                        if interactive_response != default_option and default_option not in interactive_response:
                            if isinstance(interactive_response, list):
                                possible_keys = interactive_response
                            else:
                                possible_keys = [interactive_response]
                    possible_sub_hparams = list(filter(lambda x: x[0] in possible_keys, possible_sub_hparams.items()))
                    sub_hparams = CommentedSeq() if is_list else CommentedMap()
                    for sub_key, sub_type in possible_sub_hparams:
                        eol_comment_args = {
                            "comment": f"{choice_type} of: {possible_string}",
                            "key": sub_key,
                            "column": choice_option_column,
                        }
                        if is_list:
                            sub_item = CommentedMap()
                            sub_item[sub_key] = _to_commented_map(
                                cls=sub_type,
                                **persisted_args,
                            )
                            sub_hparams.append(sub_item)
                            sub_item.yaml_add_eol_comment(**eol_comment_args)
                        else:
                            sub_hparams[sub_key] = _to_commented_map(
                                cls=sub_type,
                                **persisted_args,
                            )
                            if choice_option_column > 0:
                                sub_hparams.yaml_add_eol_comment(**eol_comment_args)

                    output[field.name] = sub_hparams
                    if choice_option_column > 0:
                        output.yaml_add_eol_comment(
                            comment=f"{choice_type} of: {possible_string}",
                            key=field.name,
                            column=choice_option_column,
                        )

    return output
