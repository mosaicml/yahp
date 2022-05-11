import abc
import dataclasses
from typing import Dict, TextIO, Type, Union

import pytest

import yahp as hp
from yahp.types import JSON


class PrimitiveClass:
    """Class

    Args:
        int_arg: Docstring
    """

    def __init__(
        self,
        int_arg: int,
    ) -> None:
        self.int_arg = int_arg


@dataclasses.dataclass
class PrimitiveClassHparams(hp.Hparams):
    int_arg: int = hp.auto(PrimitiveClass, 'int_arg')


def test_primitive_class():
    config: Dict[str, JSON] = {'int_arg': 69}
    instance = hp.create(PrimitiveClass, config)
    assert isinstance(instance, PrimitiveClass)
    assert instance.int_arg == 69


class PrimitiveClassWithDefaults:
    """Class

    Args:
        int_arg: Docstring
    """

    def __init__(
        self,
        int_arg: int = 42,
    ) -> None:
        self.int_arg = int_arg


@pytest.mark.parameterize('use_default', [True, False])
def test_primitive_class_with_defaults(use_default: bool):
    config = {}
    if not use_default:
        config['int_arg'] = 69
    instance = hp.create(PrimitiveClass, config)
    assert isinstance(instance, PrimitiveClassWithDefaults)
    assert instance.int_arg == 42 if use_default else 69


class NestedClassWithPrimitive:
    """Class

    Args:
        nested_arg: Docstring
    """

    def __init__(
        self,
        nested_arg: PrimitiveClass,
    ) -> None:
        self.nested_arg = nested_arg


class NestedClassWithHparams:

    def __init__(
        self,
        nested_arg: PrimitiveClassHparams,
    ) -> None:
        self.nested_arg = nested_arg


@pytest.mark.parametrize('cls', [NestedClassWithHparams, NestedClassWithPrimitive])
def test_nested_class(cls: Union[Type[NestedClassWithHparams], Type[NestedClassWithPrimitive]]):
    config: Dict[str, JSON] = {'nested_arg': {'int_arg': 42}}
    instance = hp.create(cls, config)
    assert isinstance(instance, cls)
    assert instance.nested_arg.int_arg == 42


class UnsupportedTypeWithUnion:
    """Class

    Args:
        file: Docstring
    """

    def __init__(
        self,
        # TextIO is not supported by yahp, but str is, so this should still work
        file: Union[str, TextIO],
    ) -> None:
        self.file = file


def test_union_with_unsupported_types(use_default: bool):
    config: Dict[str, JSON] = {'file': 'log.txt'}
    instance = hp.create(UnsupportedTypeWithUnion, config)
    assert isinstance(instance, UnsupportedTypeWithUnion)
    assert instance.file == 'log.txt'


class UnsupportedType:
    """Class

    Args:
        file: Docstring
    """

    def __init__(
        self,
        # YAHP cannot create a TextIO object from yaml
        file: TextIO,
    ) -> None:
        self.file = file


def test_unsupported_class_errors():
    with pytest.raises(
            NotImplementedError,
            match=('UnsupportedType argument `file` of type `TextIO` cannot be parsed from a config map. To fix, '
                   'use a Union with at least one supported type, or instead use an `hp.Hparams` dataclass.')):
        hp.create(UnsupportedType, {})


class AbstractClass(abc.ABC):
    pass


class ConcreteClass(AbstractClass):
    """Class

    Args:
        int_arg: Docstring
    """

    def __init__(self, int_arg: int) -> None:
        self.int_arg = int_arg


class ClassWithAbstractArg:
    """Class

    Args:
        cls: Docstring
    """

    hparams_registry = {'cls': {'concrete': ConcreteClass,}}

    def __init__(self, cls: AbstractClass) -> None:
        self.cls = cls


def test_unsupported_abstract_class_errors():
    config: Dict[str, JSON] = {'cls': {'concrete': {'int_arg': 42}}}
    instance = hp.create(ClassWithAbstractArg, config)
    assert isinstance(instance, ClassWithAbstractArg)
    assert isinstance(instance.cls, ConcreteClass)
    assert instance.cls.int_arg == 42
