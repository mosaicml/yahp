from dataclasses import MISSING, Field
from enum import Enum
from typing import Any, Sequence, Tuple, Type, Union, get_args, get_origin

import yahp
from yahp.objects_helpers import YAHPException
from yahp.utils import ensure_tuple


class _JSONDict:  # sentential for representing JSON dictionary types
    pass


_PRIMITIVE_TYPES = (bool, int, float, str)


def safe_issubclass(item, class_or_tuple) -> bool:
    return isinstance(item, type) and issubclass(item, class_or_tuple)


def _is_valid_primitive(*types: Type[Any]) -> bool:
    # only one of (bool, int, float), and optionally string, is allowed
    if not all(x in _PRIMITIVE_TYPES for x in types):
        return False
    has_bool = bool in types
    has_int = int in types
    has_float = float in types
    if has_bool + has_int + has_float > 1:
        # Unions of bools, ints, and/or floats are not supported. Pick only one.
        return False
    return True


class HparamsType:

    def __init__(self, item: Type[Any]) -> None:
        self.types, self.is_optional, self.is_list = self._extract_type(item)
        if len(self.types) == 0:
            assert self.is_optional, "invariant error"

    def _extract_type(self, item: Type[Any]) -> Tuple[Sequence[Type[Any]], bool, bool]:
        """Extracts the underlying types from a python typing object.

        Documentration is best given through examples:
        >>> _extract_type(bool) == ([bool], False, False)
        >>> _extract_type(Optional[bool])== ([bool], True, False)
        >>> _extract_type(List[bool])== ([bool], False, True)
        >>> _extract_type(List[Optional[bool]]) raises a TypeError, since Lists of optionals are not allowed by hparams
        >>> _extract_type(Optional[List[bool]]) == ([bool], True, True)
        >>> _extract_type(Optional[List[Union[str, int]]]) == ([str, int], True, True)
        >>> _extract_type(List[Union[str, int]]) == ([str, int], False, True)
        >>> _extract_type(Union[str, int]) == ([str, int], False, False)
        >>> _extract_type(Union[str, Enum]) raises a TypeError, since Enums cannot appear in non-optional Unions
        >>> _extract_type(Union[str, NoneType]) == ([str], True, False)
        >>> _extract_type(Union[str, Dataclass]) raises a TypeError, since Hparam dataclasses cannot appear in non-optional unions
        """
        origin = get_origin(item)
        if origin is None:
            # item must be simple, like None, int, float, str, Enum, or Hparams
            if item is None or item is type(None):
                return [], True, False
            if item not in _PRIMITIVE_TYPES and not safe_issubclass(item, (yahp.Hparams, Enum)):
                raise TypeError(f"item of type ({item}) is not supported.")
            is_optional = False
            is_list = False
            return [item], is_optional, is_list
        if origin is Union:
            args = get_args(item)
            is_optional = type(None) in args
            args_without_none = tuple(arg for arg in args if arg not in (None, type(None)))
            # all args in the union must be subclasses of one of the following subsets
            is_primitive = _is_valid_primitive(*args_without_none)
            is_enum = all(safe_issubclass(arg, Enum) for arg in args_without_none)
            is_hparams = all(safe_issubclass(arg, yahp.Hparams) for arg in args_without_none)
            is_list = all(get_origin(arg) is list for arg in args_without_none)
            is_json_dict = all(get_origin(arg) is dict for arg in args_without_none)
            if is_primitive or is_hparams or is_enum:
                assert is_list is False
                return args_without_none, is_optional, is_list
            if is_list:
                # Need to validate that the underlying type of list is either 1) Primitive, 2) Union of primitives
                #                 assert len(args_without_none) == 1, "should only have one one"
                assert len(args_without_none) == 1, "if here, should only have 1 non-none argument"
                list_arg = args_without_none[0]
                return self._get_list_type(list_arg), is_optional, is_list
            if is_json_dict:
                assert is_optional, "if here, then must have been is_optional"
                assert not is_list, "if here, then must not have been is_list"
                return [_JSONDict], is_optional, is_list
            raise TypeError(f"Invalid union type: {item}. Unions must be of primitive types")
        if origin is list:
            is_optional = False
            is_list = True
            return self._get_list_type(item), is_optional, is_list
        if origin is dict:
            is_optional = False
            is_list = False
            return [_JSONDict], is_optional, is_list
        raise TypeError(f"Unsupported type: {item}")

    def _get_list_type(self, list_arg: Type[Any]) -> Sequence[Type[Any]]:
        if get_origin(list_arg) is not list:
            raise TypeError("list_arg is not a List")
        list_args = get_args(list_arg)
        assert len(list_args) == 1, "lists should have exactly one argument"
        list_item = list_args[0]
        error = TypeError(f"List of type {list_item} is unsupported. Lists must be of Hparams, Enum, or a valid union.")
        list_origin = get_origin(list_item)
        if list_origin is None:
            # Must be either primitive or hparams
            if list_item not in _PRIMITIVE_TYPES and not safe_issubclass(list_item, (yahp.Hparams, Enum)):
                raise error
            return [list_item]
        if list_origin is Union:
            list_args = get_args(list_item)
            is_primitive = _is_valid_primitive(*list_args)
            if not is_primitive:
                raise error
            return list_args
        raise error

    @property
    def is_hparams_dataclass(self) -> bool:
        return len(self.types) > 0 and all(safe_issubclass(t, yahp.Hparams) for t in self.types)

    @property
    def is_json_dict(self) -> bool:
        return len(self.types) > 0 and all(safe_issubclass(t, _JSONDict) for t in self.types)

    def convert(self, val: Any) -> Any:
        # converts a value to the type specified by hparams
        # val can ether be a JSON or python representation for the value
        # Can be either a singleton or a list
        if val is None:
            if not self.is_optional:
                raise YAHPException(f"{val} is None, but a value is required.")
            return None
        if isinstance(val, (tuple, list)):
            if not self.is_list:
                raise TypeError(f"{val} is a list, but {self} is not a list")
            # If given a list, then return a list of converted values
            return type(val)(self.convert(x) for x in val)
        if self.is_enum:
            # could be a list of enums too
            enum_map = {k.name.lower(): k for k in self.type}
            enum_map.update({k.value: k for k in self.type})
            enum_map.update({k: k for k in self.type})
            if isinstance(val, str):  # if the val is a string, then check for a key match
                val = val.lower()
            return enum_map[val]
        if self.is_hparams_dataclass:
            raise NotImplementedError("convert() cannot be used with hparam dataclasses")
        if self.is_json_dict:
            if not isinstance(val, dict):
                raise TypeError(f"{val} is not a dictionary")
            return val
        if self.is_primitive:
            # could be a list of primitives
            for t in (bool, float, int, str):
                # bool, float, and int are mutually exclusive
                if t in self.types:
                    try:
                        return to_bool(val) if t is bool else t(val)
                    except (TypeError, ValueError):
                        pass
            raise TypeError(f"Unable to convert value {val} to type {self}")
        raise RuntimeError("Unknown type")

    @property
    def is_enum(self) -> bool:
        return len(self.types) > 0 and all(safe_issubclass(t, Enum) for t in self.types)

    @property
    def is_primitive(self) -> bool:
        return len(self.types) > 0 and all(safe_issubclass(t, _PRIMITIVE_TYPES) for t in self.types)

    @property
    def is_boolean(self) -> bool:
        return len(self.types) > 0 and all(safe_issubclass(t, bool) for t in self.types)

    @property
    def type(self) -> Type[Any]:
        if len(self.types) != 1:
            # self.types it not 1 in the case of unions
            raise RuntimeError(".type is not defined for unions")
        return self.types[0]

    def __str__(self) -> str:
        if self.is_primitive:  # str, float, int, bool
            if len(self.types) > 1:
                return f"One of: {', '.join(self.types)}"
            return self.type.__name__

        if self.is_enum:
            enum_values_string = ", ".join([str(x.name.lower()) for x in self.type])
            return f"Enum: {enum_values_string}"

        if self.is_list:
            return f"List of {self.type}"

        if self.is_json_dict:
            return "JSON Dictionary"

        if self.is_hparams_dataclass:
            return self.type.__name__

        if self.is_optional:
            return "None"

        raise RuntimeError("Unknown type")


def get_required_default_from_field(field: Field) -> Tuple[bool, Any]:
    default = None
    required = True
    if field.default != MISSING or field.default_factory != MISSING:
        required = False
        default = field.metadata["default"]
    return required, default


def to_bool(x: Any):
    if isinstance(x, str):
        x = x.lower()
    if x in ("t", "true", "y", "yes", 1, True):
        return True
    if x in ("f", "false", "n", "no", 0, False):
        return False
    raise ValueError(f"Could not parse {x} as bool")
