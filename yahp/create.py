from __future__ import annotations

import collections.abc
import importlib
import logging
import textwrap
from dataclasses import fields
from typing import Any, Dict, List, Type, cast, get_type_hints

from yahp import type_helpers
from yahp import yahp as hp
from yahp.objects_helpers import HparamsException
from yahp.types import JSON, THparams

logger = logging.getLogger(__name__)


def _create_from_dict(cls: Type[hp.Hparams], data: Dict[str, JSON], prefix: List[str] = []) -> hparams.Hparams:
    kwargs: Dict[str, THparams] = {}
    cls_module = importlib.import_module(cls.__module__)

    # Cast everything to the appropriate types.
    field_types = get_type_hints(cls)
    for f in fields(cls):
        ftype = field_types[f.name]
        if f.name not in data:
            # Missing field inside data
            required, default_value = type_helpers._get_required_default_from_field(field=f)
            missing_object_str = f"{ cls.__name__ }.{ f.name }"
            missing_path_string = '.'.join(prefix + [f.name])
            if required:
                raise ValueError(f"Missing required field: {missing_object_str: <30}: {missing_path_string}")
            else:
                print(
                    f"\nMissing optional field: \t{missing_object_str: <40}: {missing_path_string}\nUsing default: {default_value}"
                )
                kwargs[f.name] = default_value
        else:
            # Unwrap typing
            ftype_origin = ftype if type_helpers.get_origin(ftype) is None else type_helpers.get_origin(ftype)
            if not (type_helpers._is_hparams_type(type_helpers._get_real_ftype(ftype)) or
                    f.name in cls.hparams_registry):
                # It's a primitive type
                if type_helpers._is_optional(ftype):
                    if data[f.name] is None:
                        kwargs[f.name] = None
                    else:
                        ftype = type_helpers._get_real_ftype(ftype)
                kwargs[f.name] = type_helpers.parse_json_value(data[f.name], ftype, f"{cls.__name__}.{f.name}")
            else:
                if f.name not in cls.hparams_registry:
                    # Must be a directly nested Hparams or Optional[Hparams]
                    if data[f.name] is None:
                        if type_helpers._is_optional(ftype):
                            kwargs[f.name] = None
                            continue
                        else:
                            data[f.name] = {}
                    assert isinstance(data[f.name], dict)
                    hparams_cls = type_helpers._get_real_ftype(ftype)
                    assert issubclass(hparams_cls, hp.Hparams)
                    sub_hparams = _create_from_dict(
                        cls=hparams_cls,
                        data=cast(Dict[str, JSON], data[f.name]),
                        prefix=prefix + [f.name],
                    )
                    sub_hparams.key_name = f.name
                    kwargs[f.name] = sub_hparams
                else:
                    # Found in registry to unwrap custom Hparams subclasses
                    registry_items: Dict[str, Type[hp.Hparams]] = dict(cls._get_possible_items_for_registry_key(f.name))
                    sub_data = data[f.name]
                    # For empty Hparams with no fields
                    if sub_data is None and len(fields(ftype_origin)) == 0:
                        sub_data = {}

                    if f.name in registry_items:
                        # Direct Nesting
                        assert isinstance(sub_data, dict)
                        kwargs[f.name] = _create_from_dict(
                            cls=registry_items[f.name],
                            data=sub_data,
                            prefix=prefix + [f.name],
                        )
                    elif isinstance(sub_data, list):
                        sub_data = cast(List[Dict[str, JSON]], sub_data)
                        sub_list_hparams = [
                            _dict_to_hparams(
                                fname_key=f.name,
                                input_dict=item,
                                flat_registry=registry_items,
                                input_prefix=prefix + [f.name],
                            ) for item in sub_data
                        ]
                        kwargs[f.name] = sub_list_hparams
                    elif isinstance(sub_data, collections.abc.Mapping):
                        kwargs[f.name] = _dict_to_hparams(
                            fname_key=f.name,
                            input_dict=cast(Dict[str, Any], sub_data),
                            flat_registry=registry_items,
                            input_prefix=prefix + [f.name],
                        )
                    else:
                        logger.error(
                            textwrap.dedent(f"""\n
                        Found unexpected nested Hparams object under: {f.name}
                        """))
                        raise HparamsException("Unexpected nested Hparams format")
    return cls(**kwargs)


def _dict_to_hparams(
    fname_key: str,
    input_dict: Dict[str, Any],
    flat_registry: Dict[str, Type[hp.Hparams]],
    input_prefix: List[str],
) -> hp.Hparams:
    assert isinstance(input_dict, collections.abc.Mapping), "Should be only nesting dicts"
    for k, v in input_dict.items():
        if k in flat_registry:
            hparams_class = flat_registry[k]
            if v is None:  # For empty dataclasses
                v = {}
            new_class = _create_from_dict(
                cls=hparams_class,
                data=v,
                prefix=input_prefix + [k],
            )
            new_class.key_name = k
            return new_class
    logger.error(
        textwrap.dedent(f"""\n
    Unable to find hparams_registry key for {fname_key} at path {'.'.join(input_prefix)}
    Looked for: {', '.join(list(input_dict.keys()))}
    Found in registry: {', '.join(list(flat_registry.keys()))}
    """))
    raise HparamsException("Missing hparams_registry key")
