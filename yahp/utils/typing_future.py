# Copyright 2021 MosaicML. All Rights Reserved.

# pyright: reportUnusedImport=none
# pyright: reportMissingParameterType=none

# Future functions from typing for compatibility with python 3.7

import collections.abc
from typing import Generic, _GenericAlias  # type: ignore

try:
    from typing import get_args
except ImportError:
    # From https://github.com/python/cpython/blob/3.8/Lib/typing.py#L1292
    def get_args(tp):
        """Get type arguments with all substitutions performed.
        For unions, basic simplifications used by Union constructor are performed.
        Examples::
            get_args(Dict[str, int]) == (str, int)
            get_args(int) == ()
            get_args(Union[int, Union[T, int], str][int]) == (int, str)
            get_args(Union[int, Tuple[T, int]][str]) == (int, Tuple[str, int])
            get_args(Callable[[], T][int]) == ([], int)
        """
        if isinstance(tp, _GenericAlias) and not tp._special:
            res = tp.__args__
            if get_origin(tp) is collections.abc.Callable and res[0] is not Ellipsis:
                res = (list(res[:-1]), res[-1])
            return res
        return ()


try:
    from typing import get_origin
except ImportError:
    # From https://github.com/python/cpython/blob/3.8/Lib/typing.py#L1271
    def get_origin(tp):
        """Get the unsubscripted version of a type.
        This supports generic types, Callable, Tuple, Union, Literal, Final and ClassVar.
        Return None for unsupported types. Examples::
            get_origin(Literal[42]) is Literal
            get_origin(int) is None
            get_origin(ClassVar[int]) is ClassVar
            get_origin(Generic) is Generic
            get_origin(Generic[T]) is Generic
            get_origin(Union[T, int]) is Union
            get_origin(List[Tuple[T, T]][int]) == list
        """
        if isinstance(tp, _GenericAlias):
            return tp.__origin__
        if tp is Generic:  # type: ignore
            return Generic  # type: ignore
        return None
