# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

import json
from dataclasses import MISSING, Field
from enum import Enum
from typing import Any, Dict, Sequence, Tuple, Type, Union, cast

from yahp.utils.iter_helpers import ensure_tuple
from yahp.utils.typing_future import get_args, get_origin


class _JSONDict:  # sentential for representing JSON dictionary types
    pass


_PRIMITIVE_TYPES = (bool, int, float, str)


def safe_issubclass(item: Any, class_or_tuple: Union[Type[Any], Tuple[Type[Any], ...]]) -> bool:
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
    """Wrapper to parse type annotations and determine type of field.

    HparamsType parses typing annotations and provides convenience methods
    to determine the field types.

    Args:
        item (type): Type annotation to parse.

    Attributes:
        types (List[Type]): The allowed types for this annotation, as a list.
            If the annotation is ``List[X]`` or ``Optional[X]``,
            then ``X`` is stored in this attributed.
            If the annotation is a ``Union[X, Y]``, then this attribute
            is ``[X, Y]``. None is never stored here;
            instead, see :attr:`is_optional`.
        is_optional (bool): Whether the annotation allows None.
        is_list (bool): Whether the annotation is a list.
    """

    def __init__(self, item: Type[Any]) -> None:
        self.types, self.is_optional, self.is_list = self._extract_type(item)

        if len(self.types) == 0 and not self.is_optional:
            raise TypeError(f'Type annotation {item} is not supported')

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
        if origin is Union:
            args = cast(Sequence[Any], get_args(item))
            is_optional = type(None) in args
            args = tuple(arg for arg in args if arg not in (None, type(None)))
            is_list = all(get_origin(arg) is list for arg in args)
            if is_list:
                assert len(args) == 1, 'The list annotation takes just one argument'
                list_arg = args[0]
                return self._get_list_type(list_arg), is_optional, is_list
            is_json_dict = all(get_origin(arg) is dict for arg in args)
            if is_json_dict:
                assert is_optional, 'if here, then must have been is_optional'
                assert not is_list, 'if here, then must not have been is_list'
                return [_JSONDict], is_optional, is_list

            try:
                args = self._get_item_types(args)
            except TypeError as e:
                raise TypeError(f'Type annotation {item} is not supported') from e
            return args, is_optional, is_list

        if origin is list:
            is_optional = False
            is_list = True
            return self._get_list_type(item), is_optional, is_list
        if origin is dict:
            is_optional = False
            is_list = False
            return [_JSONDict], is_optional, is_list

        # the item can be anything
        if item is None or item is type(None):
            return [], True, False
        is_optional = False
        is_list = False
        try:
            item_types = self._get_item_types([item])
        except TypeError as e:
            raise TypeError(f'Type annotation {item} is not supported') from e
        return item_types, is_optional, is_list

    def _get_item_types(self, args: Sequence[Type[Any]]):
        # Convert any 'Any' types to be a Union[int, str, bool, float]
        # This is a best-effort solution
        # TODO(ravi) 'Any' should be treated specially -- it should also support lists and JSON dictionaries
        args = list(args)
        if any(arg == Any for arg in args):
            # remove any
            args.remove(Any)
            # Replace it with the supported types
            if int not in args:
                args.append(int)
            if bool not in args:
                args.append(bool)
            if float not in args:
                args.append(float)
            if str not in args:
                args.append(str)

        if len(args) > 1:
            # Args is a union two or more elements.
            # This function assumes that `None` was already filtered out of args
            #
            # YAHP will attempt to parse into any Enum type, then into any primitive type
            # It will not parse into any custom types that may be specified as part of a union
            # with a string or enum
            #
            # In addition, a union of multiple custom types without a primitive are not supported,
            # since yahp would not know how to parse it.

            # Determine if there is an Enum. If so, use that, and ignore all other types
            enum_classes = tuple(arg for arg in args if safe_issubclass(arg, Enum))
            if len(enum_classes) > 0:
                if len(enum_classes) > 1:
                    # Multiple enum types are not supported
                    raise TypeError(
                        f'Multiple enum classes ({", ".join(x.__name__ for x in enum_classes)}) are not supported')
                else:
                    args = enum_classes
            else:
                # Finally, filter out non primitives and non enums.
                args = tuple(arg for arg in args if _is_valid_primitive(arg))

                # If it's a union of only primitive types, that is allowed
                if len(args) == 0:
                    # If all arguments were filtered out, then it was an unsupported Union -- e.g
                    # Union[CustomClassA, CustomClassB]
                    raise TypeError(f'A union of multiple classes without a primitive or Enum are not supported')
                # Otherwise, if len(args) > 0, then there was at least one primitive or enum type that YAHP can parse
                # in to -- e.g. Union[CustomClassA, CustomClassB, str] would be filtered down to [str]

        return args

    def _get_list_type(self, list_arg: Type[Any]) -> Sequence[Type[Any]]:
        if get_origin(list_arg) is not list:
            raise TypeError('list_arg is not a List')
        list_args = get_args(list_arg)
        assert len(list_args) == 1, 'lists should have exactly one argument'
        list_item = list_args[0]
        list_origin = get_origin(list_item)
        if list_origin is None:
            # This is the singleton case
            return [list_item]
        if list_origin is Union:
            list_args = cast(Sequence[Any], get_args(list_item))

            try:
                return self._get_item_types(list_args)
            except TypeError as e:
                raise TypeError(f'Type annotation {list_arg} is not supported') from e

        raise TypeError(f'Type annotation {list_arg} is not supported')

    @property
    def is_json_dict(self) -> bool:
        """Whether it is a JSON Dictionary."""
        return len(self.types) > 0 and all(safe_issubclass(t, _JSONDict) for t in self.types)

    @property
    def is_recursive(self) -> bool:
        """Whether the datatype is recursive (i.e is not JSON, a primitive, or an enum)"""
        return not (self.is_enum or self.is_primitive or self.is_json_dict)

    def convert(self, val: Any, field_name: str, *, wrap_singletons: bool = True) -> Any:
        """Attempt to convert an item into a type allowed by the annotation.

        Args:
            val (Any): Item to convert.
            field_name (str): Name for field being converted.
            wrap_singletons (bool, optional):
                If True (the default) and the field is a list, singletons will
                be wrapped into a list. Otherwise, raise a :class:`TypeError`.

        Raises:
            ValueError: Raised if :attr:`val` is None, but
                the annotation does not permit None.
            TypeError: Raised if :attr:`val` cannot be converted into a type
                specified by the annotation.

        Returns:
            The converted item.
        """
        # converts a value to the type specified by hparams
        # val can ether be a JSON or python representation for the value
        # If a singleton is given to a list, it will be converted to a list
        if self.is_optional:
            if is_none_like(val, allow_list=self.is_list):
                return None
        if not self.is_optional and val is None:
            raise ValueError(f'{field_name} is None, but a value is required.')
        if any(isinstance(val, t) for t in self.types):
            # It is already a valid type
            return val
        if self.is_list:
            # If given a list, then return a list of converted values
            if wrap_singletons:
                return [
                    self.convert(x, f'{field_name}[{i}]', wrap_singletons=False)
                    for (i, x) in enumerate(ensure_tuple(val))
                ]
            elif isinstance(val, (tuple, list)):
                raise TypeError(f'{field_name} is a list, but wrap_singletons is false')
        if self.is_enum:
            # could be a list of enums too
            assert issubclass(self.type, Enum)
            enum_map: Dict[Union[str, Enum], Enum] = {k.name.lower(): k for k in self.type}
            enum_map.update({k.value: k for k in self.type})
            enum_map.update({k: k for k in self.type})
            if isinstance(val, str):  # if the val is a string, then check for a key match
                val = val.lower()
                if val not in enum_map:
                    possible_keys = [str(key) for key in enum_map.keys()]
                    raise ValueError(f"'{val}' is not a valid key. Choose on of {', '.join(possible_keys)}.")
            return enum_map[val]
        if self.is_json_dict:
            if isinstance(val, str):
                val = json.loads(val)
            if not isinstance(val, dict):
                raise TypeError(f'{field_name} is not a dictionary')
            return val
        if self.is_primitive:
            # could be a list of primitives
            primitive_types = [bool, float, int, str]
            # if both int and float are in self.types, then use an int if it is exact;
            # otherwise, use a float
            if float in self.types and int in self.types:
                try:
                    x_float = float(val)
                    x_int = int(x_float)
                except (TypeError, ValueError):
                    pass
                else:
                    if x_float == x_int:
                        primitive_types.remove(float)

            for t in primitive_types:

                if t in self.types:
                    try:
                        return to_bool(val) if t is bool else t(val)
                    except (TypeError, ValueError):
                        pass

            raise TypeError(f'Unable to convert value {val} for field {field_name} to type {self}')
        if isinstance(val, self.type):
            return val
        raise RuntimeError(f'convert() cannot be used with type {self.type} for field {field_name}')

    @property
    def is_enum(self) -> bool:
        """
        Whether the annotation allows for a subclass of :class:`Enum`,
        or a list of :class:`Enum`.
        """
        return len(self.types) > 0 and all(safe_issubclass(t, Enum) for t in self.types)

    @property
    def is_primitive(self) -> bool:
        """
        Whether the annotation allows for a
        :class:`bool`, :class:`int`, :class:`str`, or :class:`float`,
        a list of such types, or is always ``None``.
        """
        return all(safe_issubclass(t, _PRIMITIVE_TYPES) for t in self.types)

    @property
    def is_boolean(self) -> bool:
        """
        Whether the annotation allows for a :class:`bool`,
        or a list of :class:`bool`.
        """
        return len(self.types) > 0 and all(safe_issubclass(t, bool) for t in self.types)

    @property
    def type(self) -> Type[Any]:
        """
        The underlying type allowed by the annotation.
        If the annotation is a ``List[x]`` or ``Optional[X]``, then ``X`` is returned.

        This property is only available if the annotation is not a union
        of multiple types. For these cases, see :attr:`types`.
        """
        if len(self.types) != 1:
            # self.types it not 1 in the case of unions
            raise RuntimeError('.type is not defined for unions')
        return self.types[0]

    def __str__(self) -> str:
        if len(self.types) == 0:
            ans = None
        elif self.is_enum:
            assert issubclass(self.type, Enum)
            enum_values_string = ', '.join([x.name for x in self.type])
            ans = f'{self.type.__name__}{{{enum_values_string}}}'

        elif self.is_primitive:  # str, float, int, bool
            if len(self.types) > 1:
                ans = f"{' | '.join(t.__name__ for t in self.types)}"
            else:
                ans = self.type.__name__

        elif self.is_json_dict:
            ans = 'JSON'

        else:
            ans = ', '.join(getattr(t, '__name__', str(t)) for t in self.types)

        if ans is None:
            # always None
            return 'None'

        if self.is_list:
            ans = f'List[{ans}]'

        if self.is_optional:
            ans = f'Optional[{ans}]'
        return ans


def is_field_required(f: Field[Any]) -> bool:
    """
    Returns whether a field is required
    (i.e. does not have a default value).

    Args:
        f (Field): The field.
    """
    return get_default_value(f) == MISSING


def get_default_value(f: Field[Any]) -> Any:
    """Returns an instance of a default value for a field.

    Args:
        f (Field): The field.
    """
    if f.default != MISSING:
        return f.default
    if f.default_factory != MISSING:
        return f.default_factory()
    return MISSING


def to_bool(x: Any):
    """Converts a value to a boolean

    Args:
        x (object): Value to attempt to convert to a bool.
    """
    if isinstance(x, str):
        x = x.lower()
    if x in ('t', 'true', 'y', 'yes', 1, True):
        return True
    if x in ('f', 'false', 'n', 'no', 0, False):
        return False
    raise TypeError(f'Could not parse {x} as bool')


def is_none_like(x: Any, *, allow_list: bool) -> bool:
    """Returns whether a value is ``None``, ``"none"``, ``[""]``, ``["none"]``, or has been marked as a missing field.

    Args:
        x (object): Value to examine.
        allow_list (bool): Whether to treat ``[""]``, or ``["none"]`` as ``None``.
    """
    if x is None or x is MISSING:
        return True
    if isinstance(x, str) and x.lower() in ['', 'none']:
        return True
    if x == MISSING:
        return True
    if allow_list and isinstance(x, (tuple, list)) and len(x) == 1:
        return is_none_like(x[0], allow_list=allow_list)
    return False
