import contextlib
from dataclasses import dataclass
from typing import Dict, List, Union

import pytest

import yahp as hp


@dataclass
class Foo(hp.Hparams):
    baz: int = hp.required(doc='int')


@dataclass
class Bar(hp.Hparams):
    baz: int = hp.required(doc='int')


@dataclass
class ParentListHP(hp.Hparams):
    hparams_registry = {'foos': {'foo': Foo, 'bar': Bar}}
    foos: List[hp.Hparams] = hp.required(doc='All the foos')


@dataclass
class ParentListHPNoRegistry(hp.Hparams):
    foos: List[Foo] = hp.required(doc='All the foos')


@pytest.fixture
def baz() -> int:
    return 1


def get_data(baz: int, bar: bool = False, duplicate: bool = False, as_list: bool = False) -> Union[Dict, List]:
    """Get a data dictionary

    Args:
        baz (int): Foo param
        bar (bool, optional): Include bar? Defaults to False.
        duplicate (bool, optional): Include foo+1?. Defaults to False.
        as_list (bool, optional): Return the dictionary as a list. Defaults to False.

    Returns:
        [type]: [description]
    """
    d = {'foo': {'baz': baz}}
    if bar:
        d['bar'] = {'baz': baz}
    if duplicate:
        d['foo+1'] = {'baz': baz + 1}
    if as_list:
        if bar:
            # it's abstract
            d = dict_to_list(d)
        else:
            # it's concrete; don't prefix
            d = list(d.values())
    return d


def dict_to_list(data: Dict[str, Dict]) -> List[Dict]:
    """Convert a dictionary to a list of 1-element dictionaries.
    """
    return [{k: v} for k, v in data.items()]


@pytest.mark.parametrize('as_list', [True, False])
def test_list_without_registry(baz, as_list: bool):
    data = get_data(baz, as_list=as_list)
    ctx = contextlib.nullcontext() if as_list else pytest.warns(DeprecationWarning,
                                                                match='foos should be a list, not a dictionary')
    with ctx:
        hp = ParentListHPNoRegistry.create(data={'foos': data}, cli_args=False)

    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 1
    assert hp.foos[0].baz == baz


@pytest.mark.parametrize('as_list', [True, False])
def test_list_without_registry_duplicate(baz, as_list: bool):
    data = get_data(baz, duplicate=True, as_list=as_list)
    ctx = contextlib.nullcontext() if as_list else pytest.warns(DeprecationWarning,
                                                                match='foos should be a list, not a dictionary')
    with ctx:
        hp = ParentListHPNoRegistry.create(data={'foos': data}, cli_args=False)

    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 2
    foo0 = hp.foos[0]
    assert foo0.baz == baz
    foo1 = hp.foos[1]
    assert foo1.baz == baz + 1


def test_list_without_registry_cli_override(baz):
    data = get_data(baz)
    cli_args = ['--foos.foo.baz', str(baz + 2)]
    with pytest.warns(DeprecationWarning, match='foos should be a list, not a dictionary'):
        hp = ParentListHPNoRegistry.create(cli_args=cli_args, data={'foos': data})

    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 1
    # should be baz, not baz + 2, as we do not allow overrides for unregistered lists
    assert hp.foos[0].baz == baz


def test_list_without_registry_duplicate_cli_override(baz):
    data = get_data(baz, duplicate=True)
    cli_args = ['--foos.foo+1.baz', str(baz + 2)]
    with pytest.warns(DeprecationWarning, match='foos should be a list, not a dictionary'):
        hp = ParentListHPNoRegistry.create(cli_args=cli_args, data={'foos': data})

    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 2

    foo0 = hp.foos[0]
    assert isinstance(foo0, Foo)
    assert foo0.baz == 1

    foo1 = hp.foos[1]
    assert isinstance(foo1, Foo)
    # should be baz + 1, not baz + 2, as we do not allow overrides for unregistered lists
    assert foo1.baz == baz + 1


def test_list_with_registry(baz):
    data = get_data(baz, bar=True)
    hp = ParentListHP.create(data={'foos': data})
    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 2
    foo = hp.foos[0]
    assert isinstance(foo, Foo)
    assert foo.baz == baz

    bar = hp.foos[1]
    assert isinstance(bar, Bar)
    assert bar.baz == baz


@pytest.mark.filterwarnings('ignore:MalformedYAMLWarning')
def test_list_with_registry_passed_list(baz):
    data = get_data(baz, bar=True, as_list=True)
    hp = ParentListHP.create(data={'foos': data})
    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 2
    foo = hp.foos[0]
    assert isinstance(foo, Foo)
    assert foo.baz == baz

    bar = hp.foos[1]
    assert isinstance(bar, Bar)
    assert bar.baz == baz


def test_list_with_registry_duplicate(baz):
    data = get_data(baz, bar=True, duplicate=True)
    hp = ParentListHP.create(data={'foos': data})
    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 3
    foo0 = hp.foos[0]
    assert isinstance(foo0, Foo)
    assert foo0.baz == baz

    bar = hp.foos[1]
    assert isinstance(bar, Bar)
    assert bar.baz == baz

    foo1 = hp.foos[2]
    assert isinstance(foo1, Foo)
    assert foo1.baz == baz + 1


def test_list_with_registry_cli_override(baz):
    data = get_data(baz, bar=True)
    cli_args = ['--foos.foo.baz', str(baz + 2)]
    hp = ParentListHP.create(cli_args=cli_args, data={'foos': data})
    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 2
    foo = hp.foos[0]
    assert isinstance(foo, Foo)
    assert foo.baz == baz + 2

    bar = hp.foos[1]
    assert isinstance(bar, Bar)
    assert bar.baz == baz


@pytest.mark.filterwarnings('ignore:MalformedYAMLWarning')
def test_list_with_registry_cli_override_custom_list(baz):
    data = get_data(baz, bar=True)
    cli_args = ['--foos', 'foo']
    hp = ParentListHP.create(cli_args=cli_args, data={'foos': data})
    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 1
    foo = hp.foos[0]
    assert isinstance(foo, Foo)
    assert foo.baz == baz


def test_list_with_registry_duplicate_cli_override(baz):
    data = get_data(baz, bar=True, duplicate=True)
    cli_args = ['--foos.foo+1.baz', str(baz + 2)]
    hp = ParentListHP.create(cli_args=cli_args, data={'foos': data})
    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 3
    foo = hp.foos[0]
    assert isinstance(foo, Foo)
    assert foo.baz == baz

    bar = hp.foos[1]
    assert isinstance(bar, Bar)
    assert bar.baz == baz

    foo1 = hp.foos[2]
    assert isinstance(foo1, Foo)
    assert foo1.baz == baz + 2
