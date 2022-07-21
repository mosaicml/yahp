import inspect
from enum import Enum
from typing import Any, Dict

from yahp.utils import type_helpers


def get_registry_json_schema(f_type: type_helpers.HparamsType, registry: Dict[str, Any]):
    """Convert type into corresponding JSON Schema. As the given name is in the `hparams_registry`,
    create objects for each possible entry in the registry and treat as union type.
    """
    res = {'oneOf': []}
    for key, value in registry.items():
        res['oneOf'].append({
            'type': 'object',
            'properties': {
                key: get_type_json_schema(type_helpers.HparamsType(value))
            },
            'additionalProperties': False,
        })
    return check_for_list_and_optional(f_type, res)


def get_type_json_schema(f_type: type_helpers.HparamsType):
    """Convert type into corresponding JSON Schema.
    """
    # Import inside function to resolve circular dependencies
    from yahp.auto_hparams import ensure_hparams_cls

    res = {}

    # Union
    if len(f_type.types) > 1:
        # Add all union types using oneOf
        res = {'oneOf': []}
        for union_type in f_type.types:
            res['oneOf'].append(get_type_json_schema(type_helpers.HparamsType(union_type)))
    # Primitive Types
    elif f_type.types[0] is str:
        res = {'type': 'string'}
    elif f_type.types[0] is bool:
        res = {'type': 'boolean'}
    elif f_type.types[0] is int:
        res = {'type': 'integer'}
    elif f_type.types[0] is float:
        res = {'type': 'number'}
    # Enum
    elif inspect.isclass(f_type.types[0]) and issubclass(f_type.types[0], Enum):
        # Enum attributes can either be specified lowercase or uppercase
        member_names = [name.lower() for name in f_type.types[0]._member_names_]
        member_names.extend([name.upper() for name in f_type.types[0]._member_names_])
        res = {'enum': member_names}
    # JSON
    elif f_type.types[0] == type_helpers._JSONDict:
        res = {
            'type': 'object',
        }
    # Hparam class
    elif callable(f_type.types[0]):
        hparam_class = ensure_hparams_cls(f_type.types[0])
        res = hparam_class.get_json_schema()
    else:
        raise ValueError('Unexpected type when constructing JSON Schema.')

    return check_for_list_and_optional(f_type, res)


def check_for_list_and_optional(f_type: type_helpers.HparamsType, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap JSON Schema with list schema or optional schema if specified.
    """
    res = schema
    # Wrap type in list
    if f_type.is_list:
        res = {
            'type': 'array',
            'items': res,
        }
    # Wrap type for optional
    if f_type.is_optional:
        res = {
            'oneOf': [
                {
                    'type': 'null'
                },
                res,
            ]
        }
    return res
