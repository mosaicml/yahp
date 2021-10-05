from __future__ import annotations

import logging
from dataclasses import fields
from typing import Dict, List, Type, cast, get_type_hints

import yahp as hp
from yahp import type_helpers
from yahp.types import JSON, THparams

logger = logging.getLogger(__name__)


def _create_from_dict(cls: Type[hp.Hparams], data: Dict[str, JSON], prefix: List[str]) -> hp.Hparams:
    kwargs: Dict[str, THparams] = {}

    # Cast everything to the appropriate types.
    field_types = get_type_hints(cls)
    for f in fields(cls):
        ftype = type_helpers.HparamsType(field_types[f.name])
        field_prefix = prefix + [f.name]
        if f.name not in data:
            # Missing field inside data
            required, default_value = type_helpers.get_required_default_from_field(field=f)
            missing_object_str = f"{ cls.__name__ }.{ f.name }"
            missing_path_string = '.'.join(field_prefix)
            if required:
                raise ValueError(f"Missing required field: {missing_object_str: <30}: {missing_path_string}")
            else:
                print(
                    f"\nMissing optional field: \t{missing_object_str: <40}: {missing_path_string}\nUsing default: {default_value}"
                )
                kwargs[f.name] = default_value
        else:
            # Unwrap typing
            if not (ftype.is_hparams_dataclass or f.name in cls.hparams_registry):
                # It's a primitive type
                if ftype.is_optional:
                    if data[f.name] is None:
                        kwargs[f.name] = None
                try:
                    kwargs[f.name] = ftype.convert(data[f.name])
                except (TypeError, ValueError) as e:
                    raise type(e)(f"Unable to parse {cls.__name__}.{f.name}") from e
            else:
                if f.name not in cls.hparams_registry:
                    assert ftype.is_hparams_dataclass
                    # Must be a directly nested Hparams or Optional[Hparams]
                    if data[f.name] is None:
                        if ftype.is_optional:
                            kwargs[f.name] = None
                            continue
                        else:
                            data[f.name] = {}
                    assert isinstance(data[f.name], dict)
                    hparams_cls = ftype.type
                    assert issubclass(hparams_cls, hp.Hparams)
                    sub_hparams = _create_from_dict(
                        cls=hparams_cls,
                        data=cast(Dict[str, JSON], data[f.name]),
                        prefix=field_prefix,
                    )
                    kwargs[f.name] = sub_hparams
                else:
                    # Found in registry to unwrap custom Hparams subclasses
                    registry_items = cls.hparams_registry[f.name]
                    sub_data = data[f.name]

                    if ftype.is_list:
                        # parse by key
                        if sub_data is None:
                            sub_data = []
                        parsed_values: List[hp.Hparams] = []
                        if not isinstance(sub_data, list):
                            raise ValueError(f"{' '.join(field_prefix)} must be a list")
                        for item in sub_data:
                            if not isinstance(item, dict):
                                raise ValueError(f"{' '.join(field_prefix)} must be a dict")
                            if not len(item) == 1:
                                raise ValueError(f"{'.'.join(field_prefix)} must have just one element")
                            yaml_key, key_data = list(item.items())[0]
                            sub_prefix = field_prefix + [yaml_key]
                            if key_data is None:
                                key_data = {}
                            if not isinstance(key_data, dict):
                                raise ValueError(f"{'.'.join(sub_prefix)} must be a dict")
                            parsed_values.append(
                                _create_from_dict(
                                    cls=registry_items[yaml_key],
                                    data=key_data,
                                    prefix=sub_prefix,
                                ))
                        kwargs[f.name] = parsed_values
                    else:
                        # Direct Nesting
                        if sub_data is None:
                            sub_data = {}
                        if not isinstance(sub_data, dict):
                            raise ValueError(f"{' '.join(field_prefix)} must be a dict")
                        if not len(sub_data) == 1:
                            raise ValueError(f"{'.'.join(field_prefix)} must have just one element")
                        yaml_key, key_data = list(sub_data.items())[0]
                        if yaml_key not in registry_items:
                            raise ValueError(
                                f"Unknown key {yaml_key}. Options for {field_prefix} are: {', '.join(registry_items.keys())}."
                            )
                        sub_prefix = field_prefix + [yaml_key]
                        if key_data is None:
                            key_data = {}
                        if not isinstance(key_data, dict):
                            raise ValueError(f"{'.'.join(sub_prefix)} must be a dict")
                        kwargs[f.name] = _create_from_dict(
                            cls=registry_items[yaml_key],
                            data=key_data,
                            prefix=sub_prefix,
                        )

    return cls(**kwargs)
