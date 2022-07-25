from __future__ import annotations

import copy
import inspect
import re
from enum import Enum
from typing import Any, Dict, TextIO

from yahp.utils import type_helpers


def get_registry_json_schema(f_type: type_helpers.HparamsType, registry: Dict[str, Any], _cls_def: Dict[str, Any]):
    """Convert type into corresponding JSON Schema. As the given name is in the `hparams_registry`,
    create objects for each possible entry in the registry and treat as union type.

    Args:
        f_type (HparamsType): The type to be parsed.
        registry (Dict[str, Any]): A registry to unpack.
        _cls_def ([Dict[str, Any]]): Keeps a reference to previously built Hparmam
            classes and enums which can be used with references to make schemas more concise
            and readable.
    """
    res = {'anyOf': []}
    for key, value in registry.items():
        # Accept any string prefixed by the key. In yahp, a key can be specified multiple times using
        # key+X syntax, so prefix checking is required. Note that we assume key does not have any
        # special regex characters.
        res['anyOf'].append({
            'type': 'object',
            'patternProperties': {
                f'^{re.escape(key)}': get_type_json_schema(type_helpers.HparamsType(value), _cls_def)
            },
            'additionalProperties': False,
        })
    return _check_for_list_and_optional(f_type, res, _cls_def)


def get_type_json_schema(f_type: type_helpers.HparamsType, _cls_def: Dict[str, Any]):
    """Convert type into corresponding JSON Schema. We first check for union types and recursively
    handle each component. If a type is not union, we know it is a singleton type, so it must be
    either a primitive, Enum, JSON, or Hparam-like. Dictionaries are treated as JSON types, and
    list and optionals are handled in a post-processing step in `_check_for_list_and_optional`.

    Args:
        f_type (HparamsType): The type to be parsed.
        _cls_def ([Dict[str, Any]]): Keeps a reference to previously built Hparmam
            classes and enums which can be used with references to make schemas more concise
            and readable.
    """
    # Import inside function to resolve circular dependencies
    from yahp.auto_hparams import ensure_hparams_cls

    res = {}

    # Union
    if len(f_type.types) > 1:
        # Add all union types using anyOf
        res = {'anyOf': []}
        for union_type in f_type.types:
            res['anyOf'].append(get_type_json_schema(type_helpers.HparamsType(union_type), _cls_def))
    # Primitive Types
    elif f_type.type is str:
        res = {'type': 'string'}
    elif f_type.type is bool:
        res = {'type': 'boolean'}
    elif f_type.type is int:
        res = {'type': 'integer'}
    elif f_type.type is float:
        res = {'type': 'number'}
    # Enum
    elif inspect.isclass(f_type.type) and issubclass(f_type.type, Enum):
        # Pull schema from _cls_def
        if f_type.type in _cls_def:
            res = {'$ref': f'#/$defs/{f_type.type.__name__}'}
            _cls_def[f_type.type.__name__]['referenced'] = True
        # Otherwise build schema and add to _cls_def
        else:
            # Enum attributes can either be specified lowercase or uppercase
            member_names = [name.lower() for name in f_type.type._member_names_]
            member_names.extend([name.upper() for name in f_type.type._member_names_])
            res = {'enum': member_names}
            _cls_def[f_type.type.__name__] = copy.deepcopy(res)
            _cls_def[f_type.type.__name__]['referenced'] = False
    # JSON or unschemable types
    elif f_type.type == type_helpers._JSONDict or f_type.type == TextIO:
        res = {
            'type': 'object',
        }
    # Hparam class
    elif callable(f_type.type):
        try:
            hparam_class = ensure_hparams_cls(f_type.type)
            if hparam_class in _cls_def:
                _cls_def[hparam_class.__name__]['referenced'] = True
                res = {'$ref': f'#/$defs/{hparam_class.__name__}'}
            else:
                res = hparam_class.get_json_schema(_cls_def)
        except TypeError as e:
            # Callable fails get_type_hints in ensure_hparams_cls, which is likely because the
            # callable is a parameter to a class. As the function has not yet been specified, it
            # we cannot generate a schema for it, so we treat it as an arbitrary object
            if 'is not a module, class, method, or function' in str(e):
                res = {
                    'type': 'object',
                }
            else:
                raise
    else:
        raise ValueError('Unexpected type when constructing JSON Schema.')

    return _check_for_list_and_optional(f_type, res, _cls_def)


def _check_for_list_and_optional(f_type: type_helpers.HparamsType, schema: Dict[str, Any],
                                 _cls_def: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap JSON Schema with list schema or optional schema if specified.
    """
    res = schema

    # Use defs to avoid duplicate schema
    if f_type.is_list:
        # Use counter to give unique key name. While enums and hparams can generate unique names
        # based on classes, lists may be of primitive types, meaning we can't generate unique
        # names.
        _cls_def[f"{_cls_def['counter']}_list"] = copy.deepcopy(res)
        _cls_def[f"{_cls_def['counter']}_list"]['referenced'] = True
        res = {'$ref': f"#/$defs/{_cls_def['counter']}_list"}
        _cls_def['counter'] += 1

    # Wrap type in list, accepting singletons, and optional
    if f_type.is_list and f_type.is_optional:
        res = {
            'oneOf': [{
                'type': 'null'
            }, res, {
                'type': 'array',
                'items': res,
            }]
        }
    # Wrap type in list, accepting singletons
    elif f_type.is_list:
        res = {
            'oneOf': [res, {
                'type': 'array',
                'items': res,
            }]
        }
    # Wrap type for optional
    elif f_type.is_optional:
        res = {
            'oneOf': [
                {
                    'type': 'null'
                },
                res,
            ]
        }
    return res
