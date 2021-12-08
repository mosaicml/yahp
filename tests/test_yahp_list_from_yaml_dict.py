"""Testing needs

    5. Argparse override with list  without registry - F
    7. Argparse override with list without registry with duplicate - F
    8. Argparse override with list with registry with duplicate - F
    10. List object without registry with list yaml - F
"""

from dataclasses import dataclass
from typing import List

import pytest

import yahp as hp


@dataclass
class Foo(hp.Hparams):
    baz: int = hp.required(doc="int")


@dataclass
class Bar(hp.Hparams):
    baz: int = hp.required(doc="int")


@dataclass
class ParentListHP(hp.Hparams):
    hparams_registry = {"foos": {"foo": Foo, "bar": Bar}}
    foos: List[hp.Hparams] = hp.required(doc="All the foos")


@dataclass
class ParentListHPNoRegistry(hp.Hparams):
    foos: List[Foo] = hp.required(doc="All the foos")


@pytest.fixture
def baz():
    return 1


@pytest.fixture
def duplicate():
    return False


@pytest.fixture
def bar():
    return True


@pytest.fixture(params=(False, True))
def as_list(request):
    return request.param


def get_data(baz, bar=False, duplicate=False, as_list=False):
    d = {"foo": {"baz": baz}}
    if bar:
        d["bar"] = {"baz": baz}
    if duplicate:
        d["foo+1"] = {"baz": baz + 1}
    if as_list:
        d = dict_to_list(d)
    return d


def dict_to_list(data):
    return [{k: v} for k, v in data.items()]


@pytest.fixture
def parent_list_hp(data):
    return ParentListHP.create(data={"foos": data})


@pytest.fixture
def parent_list_hp_no_registry(data):
    return ParentListHPNoRegistry.create(data=data)


def test_list_without_registry(baz):
    data = get_data(baz)
    hp = ParentListHPNoRegistry.create(data={"foos": data})

    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 1
    assert hp.foos[0].baz == baz


@pytest.mark.filterwarnings("ignore:MalformedYAMLWarning")
def test_list_without_registry_passed_list(baz):
    data = get_data(baz, as_list=True)
    hp = ParentListHPNoRegistry.create(data={"foos": data})

    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 1
    assert hp.foos[0].baz == baz


def test_list_without_registry_duplicate(baz):
    data = get_data(baz, duplicate=True)
    hp = ParentListHPNoRegistry.create(data={"foos": data})

    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 2
    foo0 = hp.foos[0]
    assert foo0.baz == baz
    foo1 = hp.foos[1]
    assert foo1.baz == baz + 1


# Expected to fail while we do not allow CLI overrides of unregistered lists
@pytest.mark.xfail
def test_list_without_registry_cli_override(baz):
    data = get_data(baz)
    cli_args = ["--foos.foo.baz", str(baz + 2)]
    hp = ParentListHPNoRegistry.create(cli_args=cli_args, data={"foos": data})

    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 1
    assert hp.foos[0].baz == baz + 2


# Expected to fail while we do not allow CLI overrides of unregistered lists
@pytest.mark.xfail
def test_list_without_registry_duplicate_cli_override(baz):
    data = get_data(baz, duplicate=True)
    cli_args = ["--foos.foo+1.baz", str(baz + 2)]
    hp = ParentListHPNoRegistry.create(cli_args=cli_args, data={"foos": data})

    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 2

    foo0 = hp.foos[0]
    assert isinstance(foo0, Foo)
    assert foo0.baz == 1

    foo1 = hp.foos[1]
    assert isinstance(foo1, Foo)
    assert foo1.baz == baz + 2


def test_list_with_registry(baz):
    data = get_data(baz, bar=True)
    hp = ParentListHP.create(data={"foos": data})
    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 2
    foo = hp.foos[0]
    assert isinstance(foo, Foo)
    assert foo.baz == baz

    bar = hp.foos[1]
    assert isinstance(bar, Bar)
    assert bar.baz == baz


@pytest.mark.filterwarnings("ignore:MalformedYAMLWarning")
def test_list_with_registry_passed_list(baz):
    data = get_data(baz, bar=True, as_list=True)
    hp = ParentListHP.create(data={"foos": data})
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
    hp = ParentListHP.create(data={"foos": data})
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
    cli_args = ["--foos.foo.baz", str(baz + 2)]
    hp = ParentListHP.create(cli_args=cli_args, data={"foos": data})
    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 2
    foo = hp.foos[0]
    assert isinstance(foo, Foo)
    assert foo.baz == baz + 2

    bar = hp.foos[1]
    assert isinstance(bar, Bar)
    assert bar.baz == baz


@pytest.mark.filterwarnings("ignore:MalformedYAMLWarning")
def test_list_with_registry_cli_override_custom_list(baz):
    data = get_data(baz, bar=True)
    cli_args = ["--foos", "foo"]
    hp = ParentListHP.create(cli_args=cli_args, data={"foos": data})
    assert isinstance(hp.foos, list)
    assert len(hp.foos) == 1
    foo = hp.foos[0]
    assert isinstance(foo, Foo)
    assert foo.baz == baz


#@pytest.mark.xfail
def test_list_with_registry_duplicate_cli_override(baz):
    data = get_data(baz, bar=True, duplicate=True)
    cli_args = ["--foos.foo+1.baz", str(baz + 2)]
    hp = ParentListHP.create(cli_args=cli_args, data={"foos": data})
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


if __name__ == "__main__":
    baz = 1
    data = get_data(baz, bar=True, duplicate=True)
    cli_args = ["--foos.foo+1.baz", str(baz + 2)]
    hp = ParentListHP.create(cli_args=cli_args, data={"foos": data})
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
