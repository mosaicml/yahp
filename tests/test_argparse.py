import pytest

from tests.yahp_fixtures import ListHparam, OptionalBooleansHparam, YamlInput


def test_boolean_overrides_explicit(empty_object_yaml_input: YamlInput):
    o = OptionalBooleansHparam.create(
        filepath=empty_object_yaml_input.filename,
        args=['--default_true', 'false', '--default_false', 'true'],
    )
    assert o.default_true == False  # type: ignore
    assert o.default_false == True  # type: ignore


def test_boolean_overrides_implicit(empty_object_yaml_input: YamlInput):
    o = OptionalBooleansHparam.create(
        filepath=empty_object_yaml_input.filename,
        args=['--default_true', '--default_false'],
    )
    assert o.default_true == True  # type: ignore
    assert o.default_false == True  # type: ignore


def test_list_hparam(empty_object_yaml_input: YamlInput):
    o = ListHparam.create(
        filepath=empty_object_yaml_input.filename,
        args=['--list_of_str', 'one', 'two'],
    )

    print(o)
    assert isinstance(o, ListHparam)
    assert isinstance(o.list_of_str, list)
    assert isinstance(o.list_of_int, list)
    assert isinstance(o.list_of_str[0], str)
    assert len(o.list_of_str) == 2
    assert len(o.list_of_int) == 0
    assert o.list_of_str[0] == "one"
    assert isinstance(o.list_of_str[1], str)
    assert o.list_of_str[1] == "two"


@pytest.mark.xfail
def test_list_hparam_int(empty_object_yaml_input: YamlInput):
    o = ListHparam.create(
        filepath=empty_object_yaml_input.filename,
        args=['--list_of_int', '1', '2'],
    )

    assert isinstance(o, ListHparam)
    assert isinstance(o.list_of_str, list)
    assert isinstance(o.list_of_int, list)
    assert isinstance(o.list_of_int[0], str)
    assert o.list_of_str[0] == 0
    assert isinstance(o.list_of_str[1], str)
    assert o.list_of_str[1] == 2
