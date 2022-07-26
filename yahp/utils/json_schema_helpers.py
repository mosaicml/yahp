from __future__ import annotations

import copy
import inspect
import re
from enum import Enum
from typing import Any, Dict

from yahp.utils import type_helpers


def get_registry_json_schema(f_type: type_helpers.HparamsType, registry: Dict[str, Any], _cls_def: Dict[str, Any],
                             allow_recursion: bool):
    """Convert type into corresponding JSON Schema. As the given name is in the `hparams_registry`,
    create objects for each possible entry in the registry and treat as union type.

    Args:
        f_type (HparamsType): The type to be parsed.
        registry (Dict[str, Any]): A registry to unpack.
        _cls_def ([Dict[str, Any]]): Keeps a reference to previously built Hparmam
            classes and enums which can be used with references to make schemas more concise
            and readable.
        allow_recursion (bool): Indicates whether parent Hparam class was autoyahp generated
    """
    res = {'anyOf': []}
    for key in sorted(registry.keys()):
        # Accept any string prefixed by the key. In yahp, a key can be specified multiple times using
        # key+X syntax, so prefix checking is required
        res['anyOf'].append({
            'type': 'object',
            'patternProperties': {
                f'^{re.escape(key)}($|\\+)':
                    get_type_json_schema(type_helpers.HparamsType(registry[key]), _cls_def, allow_recursion)
            },
            'additionalProperties': False,
        })
    return _check_for_list_and_optional(f_type, res, _cls_def)


def get_type_json_schema(f_type: type_helpers.HparamsType, _cls_def: Dict[str, Any], allow_recursion: bool):
    """Convert type into corresponding JSON Schema. We first check for union types and recursively
    handle each component. If a type is not union, we know it is a singleton type, so it must be
    either a primitive, Enum, JSON, or Hparam-like. Dictionaries are treated as JSON types, and
    list and optionals are handled in a post-processing step in `_check_for_list_and_optional`.

    Args:
        f_type (HparamsType): The type to be parsed.
        _cls_def ([Dict[str, Any]]): Keeps a reference to previously built Hparmam
            classes and enums which can be used with references to make schemas more concise
            and readable.
        allow_recursion (bool): Indicates whether parent Hparam class was autoyahp generated
    """
    # Import inside function to resolve circular dependencies
    from yahp.auto_hparams import ensure_hparams_cls

    res = {}

    # Union
    if len(f_type.types) > 1:
        # Add all union types using anyOf
        res = {'anyOf': []}
        for union_type in f_type.types:
            res['anyOf'].append(get_type_json_schema(type_helpers.HparamsType(union_type), _cls_def, allow_recursion))
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
        # Build schema and add to _cls_def if not present
        if f_type.type.__qualname__ not in _cls_def:
            # Enum attributes can either be specified lowercase or uppercase
            member_names = [name.lower() for name in f_type.type._member_names_]
            member_names.extend([name.upper() for name in f_type.type._member_names_])
            for name in f_type.type:
                name = name.value
                if type(name) == str:
                    member_names.extend([name.upper(), name.lower()])
                else:
                    member_names.append(name)
            member_names = sorted(list(set(member_names)), key=lambda x: str(x))
            res = {'enum': member_names}
            _cls_def[f_type.type.__qualname__] = copy.deepcopy(res)
        res = {'$ref': f'#/$defs/{f_type.type.__qualname__}'}
    # JSON or unschemable types
    elif f_type.type == type_helpers._JSONDict:
        res = {
            'type': 'object',
        }
    # Hparam class
    elif callable(f_type.type):
        # If the parent class was autoyahped, do not try autoyahping parameters
        if allow_recursion:
            res = {
                'type': 'object',
            }
        # Otherwise, attempt to autoyahp
        else:
            hparam_class = ensure_hparams_cls(f_type.type)
            # Build schema and add to _cls_def if not present. _get_json_schema adds to _cls_def
            # internally, so we only need to call the function.
            if hparam_class not in _cls_def:
                hparam_class._get_json_schema(_cls_def)
            res = {'$ref': f'#/$defs/{hparam_class.__qualname__}'}
    else:
        raise ValueError('Unexpected type when constructing JSON Schema.')

    return _check_for_list_and_optional(f_type, res, _cls_def)


def _check_for_list_and_optional(f_type: type_helpers.HparamsType, schema: Dict[str, Any],
                                 _cls_def: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap JSON Schema with list schema or optional schema if specified.
    """
    if not f_type.is_list and not f_type.is_optional:
        return schema

    # Accept singletons
    res = {'oneOf': [schema]}
    # Wrap type in list
    if f_type.is_list:
        res['oneOf'].append({
            'type': 'array',
            'items': schema,
        })
    # Wrap type for optional
    if f_type.is_optional:
        res['oneOf'].append({'type': 'null'})

    # Explicitly shortcut primitives
    if len(f_type.types) == 1 and f_type.type in (str, bool, int, float):
        key_name = f"{f_type.type.__qualname__}{'_list' if f_type.is_list else ''}{'_optional' if f_type.is_optional else ''}"
        if key_name not in _cls_def:
            _cls_def[key_name] = copy.deepcopy(res)
        res = {'$ref': f'#/$defs/{key_name}'}

    return res
