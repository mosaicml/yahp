import pytest

from tests.yahp_fixtures import OptionalBooleansHparam, YamlInput


def test_boolean_overrides_explicit(empty_object_yaml_input: YamlInput):
    o = OptionalBooleansHparam.create(filepath=empty_object_yaml_input.filename,
                                      args=['--default_true', 'false', '--default_false', 'true'])
    assert o.default_true == False  # type: ignore
    assert o.default_false == True  # type: ignore


def test_boolean_overrides_implicit(empty_object_yaml_input: YamlInput):
    o = OptionalBooleansHparam.create(filepath=empty_object_yaml_input.filename,
                                      args=['--default_true', '--default_false'])
    assert o.default_true == True  # type: ignore
    assert o.default_false == True  # type: ignore
