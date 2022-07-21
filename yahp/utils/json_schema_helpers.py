import inspect
from enum import Enum

from yahp.utils import type_helpers


def get_type_json_schema(f_type: type_helpers.HparamsType):
    # Import inside function to resovle circular dependencies
    from yahp.auto_hparams import ensure_hparams_cls

    res = {}
    # List
    if f_type.is_list:
        res = {'type': 'array', 'items': {'type': get_list_type_json_schema(f_type)}}
        # Remove additional properties if its empty, such as if value_type is JSON
        if len(res['items']['type'].keys()) == 0:
            del res['items']
    # Union
    if len(f_type.types) > 1:
        res = get_list_type_json_schema(f_type)
    # Primitive Types
    if f_type.types[0] is str:
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
    elif f_type.types[0] == type_helpers._JSONDict:
        res = {
            'type': 'object',
        }
    # Hparam class
    elif callable(f_type.types[0]):
        hparam_class = ensure_hparams_cls(f_type.types[0])
        return hparam_class.get_json_schema()
    # JSON
    else:
        raise ValueError('Unexpected type when constructing JSON Schema.')
    if f_type.is_optional:
        res = {
            'anyOf': [
                {
                    'type': 'null'
                },
                res,
            ]
        }
    return res


def get_list_type_json_schema(f_type: type_helpers.HparamsType):
    if len(f_type.types) > 1:
        # Add all union types using oneOf
        res = {'oneOf': []}
        for union_type in f_type.types:
            res['oneOf'].append(get_list_type_json_schema(type_helpers.HparamsType(union_type)))
    else:
        res = {'type': f_type.types[0]}
    return res
