import abc
import dataclasses
from typing import Any, Callable, Dict, Optional, TextIO, Type, Union

import pytest

import yahp as hp
from yahp.auto_hparams import generate_hparams_cls
from yahp.serialization import serialize
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


class PrimitiveClassWithStringAnnotations:
    """Class

    Args:
        int_arg: Docstring
    """

    def __init__(
        self,
        int_arg: 'int',
    ) -> None:
        self.int_arg = int_arg


@pytest.mark.parametrize('cls', [PrimitiveClass, PrimitiveClassWithStringAnnotations])
def test_primitive_class(cls: Union[Type[PrimitiveClass], Type[PrimitiveClassWithStringAnnotations]]):
    config: Dict[str, JSON] = {'int_arg': 69}
    instance = hp.create(cls, config)
    assert isinstance(instance, cls)
    assert instance.int_arg == 69

    assert serialize(instance) == config


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

    assert serialize(instance) == {'int_arg': 42 if use_default else 69}


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


@dataclasses.dataclass
class PrimitiveClassHparams(hp.Hparams):
    int_arg: int = hp.auto(PrimitiveClass, 'int_arg')


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

    assert serialize(instance) == config


class ClassWithDoubleNestingNonHparams:
    """Class

    Args:
        nested_arg: Docstring
    """

    def __init__(
        self,
        nested_arg: ClassWithNestedNonHparams,
    ) -> None:
        self.nested_arg = nested_arg


def test_class_with_double_nesting_non_hparams_errors():
    # Double nesting is not allowed -- can create hairy type errors.
    config: Dict[str, JSON] = {'nested_arg': {'nested_arg': {'int_arg': 42}}}
    with pytest.raises(TypeError):
        hp.create(ClassWithDoubleNestingNonHparams, config)


class ClassWithDoubleNestingHparams:
    """Class

    Args:
        nested_arg: Docstring
    """

    def __init__(
        self,
        nested_arg: ClassWithNestedHparams,
    ) -> None:
        self.nested_arg = nested_arg


def test_class_with_double_nesting_with_hparams():
    # Double nesting is not allowed -- can create hairy type errors.
    config: Dict[str, JSON] = {'nested_arg': {'nested_arg': {'int_arg': 42}}}
    instance = hp.create(ClassWithDoubleNestingHparams, config)
    assert isinstance(instance, ClassWithDoubleNestingHparams)
    assert instance.nested_arg.nested_arg.int_arg == 42

    assert serialize(instance) == config


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

    assert serialize(instance) == config


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
    msg = (
        r"Argument filename with type annotation \<class 'typing\.TextIO'\> is abstract; however, abstract types are not supported "
        r'without the concrete implementations defined in the hparams_registry')

    with pytest.raises(TypeError, match=msg):
        unsupported_type = hp.create(UnsupportedType, {})
        print(unsupported_type)


class UnsupportedTypeWithOptional:
    """Class

    Args:
        filename: Docstring
    """

    def __init__(
        self,
        # YAHP cannot create a TextIO object from yaml
        # but it should still be able to parse this class and set the field to None
        filename: Optional[TextIO],
    ) -> None:
        self.filename = filename


def test_unsupported_type_with_optional():
    config: Dict[str, JSON] = {'filename': None}
    instance = hp.create(UnsupportedTypeWithOptional, config)
    assert isinstance(instance, UnsupportedTypeWithOptional)
    assert instance.filename is None
    assert serialize(instance) == config


def foo(a: int, b: float):
    """Foo.

    Args:
        a (int): A.
        b (float): B.
    """
    return lambda: a * b


class UnsupportedTypeWithRegistry:
    """Class

    Args:
        func: Function
    """
    hparams_registry = {'func': {'foo': foo}}

    def __init__(
        self,
        func: Callable,
    ) -> None:
        self.func = func


def test_unsupported_type_with_registry():
    config: Dict[str, JSON] = {'func': {'foo': {'a': 5, 'b': 3.0}}}
    instance = hp.create(UnsupportedTypeWithRegistry, config)
    assert isinstance(instance, UnsupportedTypeWithRegistry)
    assert instance.func() == 15
    assert serialize(instance) == config


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
    assert serialize(instance) == config


@dataclasses.dataclass
class ClassWithMixedHparamsRegistry(hp.Hparams):
    """Class

    Args:
        item (AbstractClass): Docstring.
    """

    hparams_registry = {
        'item': {
            'concrete': ConcreteClass,
            'auto_initialized': generate_hparams_cls(ConcreteClass),
        }
    }

    item: AbstractClass = hp.required('item')

    def __init__(self, item: AbstractClass) -> None:
        self.item = item


@pytest.mark.parametrize('key', ['concrete', 'auto_initialized'])
def test_class_with_mixed_hparams_registry(key: str):
    config: Dict[str, JSON] = {'item': {key: {'int_arg': 42}}}
    instance = hp.create(ClassWithMixedHparamsRegistry, config)
    assert isinstance(instance, ClassWithMixedHparamsRegistry)
    assert isinstance(instance.item, ConcreteClass)
    assert instance.item.int_arg == 42
    assert serialize(instance) == config


class ClassWithAny:
    """Class

    Args:
        any_arg: Docstring
    """

    def __init__(self, any_arg: Any) -> None:
        self.any_arg = any_arg


@pytest.mark.parametrize('any_arg', [True, 3.14, 69, 'hello'])
def test_any_arg(any_arg: Any):
    config = {'any_arg': any_arg}
    instance = hp.create(ClassWithAny, config)
    assert type(instance.any_arg) == type(any_arg)
    assert instance.any_arg == any_arg
    assert serialize(instance) == config
