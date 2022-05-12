import abc
import dataclasses
from typing import Dict, TextIO, Type, Union

import pytest

import yahp as hp
from yahp.auto_hparams import generate_hparams_cls
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


@pytest.mark.parametrize('use_default', [True, False])
def test_primitive_class_with_defaults(use_default: bool):
    config = {}
    if not use_default:
        config['int_arg'] = 69
    instance = hp.create(PrimitiveClassWithDefaults, config)
    assert isinstance(instance, PrimitiveClassWithDefaults)
    assert instance.int_arg == 42 if use_default else 69


class ClassWithNestedNonHparams:
    """Class

    Args:
        nested_arg: Docstring
    """

    def __init__(
        self,
        nested_arg: PrimitiveClass,
    ) -> None:
        self.nested_arg = nested_arg


class ClassWithNestedHparams:
    """Class

    Args:
        nested_arg: Docstring
    """

    def __init__(
        self,
        nested_arg: PrimitiveClassHparams,
    ) -> None:
        self.nested_arg = nested_arg


@pytest.mark.parametrize('cls', [ClassWithNestedHparams, ClassWithNestedNonHparams])
def test_class_with_nested_hparams(cls: Union[Type[ClassWithNestedHparams], Type[ClassWithNestedNonHparams]]):
    config: Dict[str, JSON] = {'nested_arg': {'int_arg': 42}}
    instance = hp.create(cls, config)
    assert isinstance(instance, cls)
    assert instance.nested_arg.int_arg == 42


class UnionWithSupportedAndUnsupportedType:
    """Class

    Args:
        filename: Docstring
    """

    def __init__(
        self,
        # TextIO is not supported by yahp, but str is, so this should still work
        filename: Union[str, TextIO],
    ) -> None:
        self.filename = filename


def test_union_with_unsupported_types():
    config: Dict[str, JSON] = {'filename': 'log.txt'}
    instance = hp.create(UnionWithSupportedAndUnsupportedType, config)
    assert isinstance(instance, UnionWithSupportedAndUnsupportedType)
    assert instance.filename == 'log.txt'


class UnsupportedType:
    """Class

    Args:
        filename: Docstring
    """

    def __init__(
        self,
        # YAHP cannot create a TextIO object from yaml
        filename: TextIO,
    ) -> None:
        self.filename = filename


def test_unsupported_class_errors():
    with pytest.raises(TypeError, match=(r"Type annotation <class 'typing\.TextIO'> is not supported")):
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


@dataclasses.dataclass
class DataclassWithAbstractClass(hp.Hparams):
    item: AbstractClass = hp.required('item')

    hparams_registry = {'item': {'concrete': ConcreteClass,}}


def test_dataclass_with_abstract_class():
    config: Dict[str, JSON] = {'item': {'concrete': {'int_arg': 42}}}
    instance = hp.create(DataclassWithAbstractClass, config)
    assert isinstance(instance, DataclassWithAbstractClass)
    assert isinstance(instance.item, ConcreteClass)
    assert instance.item.int_arg == 42


class ClassWithMixedHparamsRegistry:
    """Class

    Args:
        cls (AbstractClass): Docstring.
    """

    hparams_registry = {
        'cls': {
            'concrete': ConcreteClass,
            'auto_initialized': generate_hparams_cls(ConcreteClass),
        }
    }

    def __init__(self, cls: AbstractClass) -> None:
        self.cls = cls


@pytest.mark.parametrize('key', ['concrete', 'auto_initialized'])
def test_class_with_mixed_hparams_registry(key: str):
    config: Dict[str, JSON] = {'cls': {key: {'int_arg': 42}}}
    instance = hp.create(ClassWithMixedHparamsRegistry, config)
    assert isinstance(instance, ClassWithMixedHparamsRegistry)
    assert isinstance(instance.cls, ConcreteClass)
    assert instance.cls.int_arg == 42
