import collections.abc
from dataclasses import MISSING, Field
from enum import Enum
from typing import Any, Dict, Tuple, Type, Union, get_args, get_origin

import yahp as hp
from yahp.objects_helpers import YAHPException
from yahp.types import JSON, THparams


def _is_hparams_type(item: Any) -> bool:
    return _safe_subclass_checker(item, hp.Hparams)


def _safe_subclass_checker(item: Any, check_class: Any) -> bool:
    return isinstance(item, type) and issubclass(item, check_class)


def _is_boolean_optional_type(item: Any) -> bool:
    # Returns true if item is bool or Optional[bool]
    if _is_optional(item):
        item = _get_real_ftype(item)
    return _safe_subclass_checker(item, bool)


def _is_primitive_optional_type(item: Any) -> bool:
    # Returns true if item is:
    # 1. None
    # 2. str/float/int (bool is a type of int)
    # 3. Enum
    # 4. Optional[any of the above]
    if _is_optional(item):
        item = _get_real_ftype(item)
    return _is_primitive_type(item)


def _is_primitive_type(item: Any) -> bool:
    # Returns true if item is:
    # 1. None
    # 2. str/float/int (bool is a type of int)
    # 3. Enum
    if _is_none_like(item):
        return True
    return _safe_subclass_checker(item, (str, float, int, Enum))


def _is_enum_type(item: Any) -> bool:
    return _safe_subclass_checker(item, (Enum))


def _is_list(item: Any) -> bool:
    origin = get_origin(item)
    item = item if origin is None else origin
    return _safe_subclass_checker(item, list)


def _is_none_like(item: object) -> bool:
    return item is None or item is type(None)


def _is_optional(item: Any) -> bool:
    origin, args = get_origin(item), get_args(item)
    if origin is None:
        return False
    if origin is not Union:
        return False
    return type(None) in args


def _is_json_dict(item: Any) -> bool:
    origin = get_origin(item)
    if origin is None:
        return False
    if not _safe_subclass_checker(origin, collections.abc.Mapping):
        return False
    key_type, val_type = get_args(item)
    if key_type is not str:
        return False
    # TODO(ravi) because of the recursive definition of JSON,
    # val_type != JSON even if it is indeed JSON
    # Instead, we assume that any Dict[str, ...] is Dict[str, JSON]
    # if val_type != JSON:
    #     return False
    return True


def _get_real_ftype(item: Any) -> Type[THparams]:
    # Returns the underlying type, ignoring optionals
    # If the underlying type is a collection or non-optional union, raises
    # a TypeError
    # Example: int -> int
    #          Optional[Hparams] -> Hparams
    #          Union[Hparams, None] -> Hparams  # same as above
    #          None -> None
    #          NoneType -> NoneType
    if _is_none_like(item) or _is_primitive_type(item) or _is_hparams_type(item):
        return item
    origin, args = get_origin(item), get_args(item)
    if origin is None:
        raise TypeError(f"Invalid type {item}")
    if origin is Union:
        if len(args) != 2 or type(None) not in args:
            raise TypeError(f"Invalid type {item}")
        return _get_real_ftype(args[1]) if _is_none_like(args[0]) else _get_real_ftype(args[0])
    if origin is list:
        assert len(args) == 1
        return _get_real_ftype(args[0])
    if origin is dict:
        return origin
    raise TypeError(f"Invalid type {item}")


def _get_type_name(item: Type[THparams]) -> str:
    if item is None:
        return "None"
    origin, args = get_origin(item), get_args(item)
    if origin is None:
        assert _is_primitive_optional_type(item) or _is_hparams_type(item)
        if _is_enum_type(item):
            assert issubclass(item, Enum)
            enum_values_string = ", ".join([str(x.name.lower()) for x in item])
            return f"Enum: {enum_values_string}"
        return item.__name__
    if _is_list(item):
        assert len(args) == 1
        arg, = args
        # We don't allow lists of unions
        assert _is_primitive_optional_type(arg) or _is_hparams_type(arg)
        assert arg is not None  # List of Nones doesn't make sense
        if _is_enum_type(arg):
            return f"List of: {_get_type_name(arg)}"
        return f"List of: {arg.__name__}"

    if _is_json_dict(item):
        return "JSON Dictionary"

    if origin is Union:
        ans = []
        for arg in args:
            if _is_none_like(arg):
                ans.append("None")
                continue
            if _is_primitive_optional_type(arg) or _is_hparams_type(arg):
                ans.append(arg.__name__)
                continue
            raise TypeError("Only unions of primitive types are supported.")
        return "Union of: " + ", ".join(ans)

    raise TypeError(f"Unknown type for item: {type(item)}")


def _get_required_default_from_field(field: Field) -> Tuple[bool, Any]:
    default = None
    required = True
    if field.default != MISSING or field.default_factory != MISSING:
        required = False
        default = field.metadata["default"]
    return required, default


def parse_json_value(val: JSON, ftype: Type, name: str) -> Any:

    if val is None:
        if not _is_optional(ftype):
            raise YAHPException(f"{name} is None, but a value is required.")
        return None
    elif _is_primitive_optional_type(ftype):
        if _safe_subclass_checker(ftype, Enum):
            assert isinstance(ftype, type) and issubclass(ftype, Enum)
            entries: Dict[str, str] = {k.name.lower(): k.name for k in ftype}
            passed_key = str(val).lower()
            if passed_key in entries:
                return ftype[entries[passed_key]]  # type: ignore
            # Try to find a value match
            val_entries: Dict[Any, str] = {k.value: k.name for k in ftype}
            if val in val_entries:
                return ftype[val_entries[val]]
            if len(val_entries.values()) and type(list(val_entries.values())[0]) != type(val):
                try:
                    # Try autocasting to value if lost on argparse
                    new_val = type(list(val_entries.values())[0])(val)
                    if new_val in val_entries:
                        return ftype[val_entries[new_val]]
                except:
                    # Probably failed casting
                    pass

            raise TypeError(f"Failed to instantiate an enum of type: {ftype} with value: {val}")
        else:
            real_ftype = _get_real_ftype(ftype)
            if real_ftype is float and isinstance(val, int):
                val = float(val)
            if real_ftype is bool and val in (0, 1):
                val = bool(val)
            if not isinstance(val, real_ftype):
                raise TypeError(
                    f"{name} must be a {_get_type_name(ftype)}; instead received {val} of type {type(val).__name__}")
            return val
    elif _is_list(ftype):
        inner_list_type = _get_real_ftype(ftype)
        ans = []
        if not isinstance(val, list):
            raise TypeError(f"{name} must be a list; instead received {val} of type {type(val).__name__}")
        for i, arg in enumerate(val):
            ans.append(parse_json_value(arg, inner_list_type, f"{name}[{i}]."))
        return ans
    elif _is_json_dict(ftype):
        return val
    raise TypeError(f"Invalid type for {name}: {ftype}")
