import pathlib
from typing import List, Union

import pytest

import yahp as hp
from tests.yahp_fixtures import YamlInput, generate_named_tuple_from_data


class InnerClassOne:

    def __init__(
        self,
        int_field: int,
    ):
        self.int_field = int_field


class InnerClassTwo:

    def __init__(
        self,
        float_field: float,
    ):
        self.float_field = float_field


@hp.override_parameter_type('union_field', InnerClassOne)
class ClassUnionClass:

    def __init__(self, union_field: Union[InnerClassOne, InnerClassTwo]):
        self.union_field = union_field


@pytest.fixture
def class_union_asset_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    return generate_named_tuple_from_data(hparams_tempdir=hparams_tempdir,
                                          input_data={"union_field": {
                                              "int_field": 7
                                          }},
                                          filepath="ppv_asset.yaml")


def test_class_union_asset_hparams_data(class_union_asset_yaml_input: YamlInput):
    o = hp.create(ClassUnionClass, data=class_union_asset_yaml_input.dict_data)

    assert isinstance(o.union_field, InnerClassOne)
    assert o.union_field.int_field == 7


def test_class_union_asset_hparams_file(class_union_asset_yaml_input: YamlInput):
    o = hp.create(ClassUnionClass, f=class_union_asset_yaml_input.filename)

    assert isinstance(o.union_field, InnerClassOne)
    assert o.union_field.int_field == 7


@hp.create_subclass_registry()
class ChoiceClass:
    pass


class OptionOneClass(ChoiceClass, canonical_name="option_one"):

    def __init__(self, int_field: int):
        self.int_field = int_field


class OptionTwoClass(ChoiceClass, canonical_name="option_two"):

    def __init__(self, string_field: str):
        self.string_field = string_field


@hp.override_parameter_type('union_field', ChoiceClass)
class ChoiceUnionClass:

    def __init__(
        self,
        union_field: Union[ChoiceClass, int],
    ):
        self.union_field = union_field


@pytest.fixture
def choice_union_asset_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    return generate_named_tuple_from_data(hparams_tempdir=hparams_tempdir,
                                          input_data={"union_field": {
                                              "option_two": {
                                                  "string_field": "foobar"
                                              },
                                          }},
                                          filepath="ppv_asset.yaml")


def test_choice_union_asset_hparams_data(choice_union_asset_yaml_input: YamlInput):
    o = hp.create(ChoiceUnionClass, data=choice_union_asset_yaml_input.dict_data)

    assert isinstance(o.union_field, OptionTwoClass)
    assert o.union_field.string_field == "foobar"


def test_choice_union_asset_hparams_file(choice_union_asset_yaml_input: YamlInput):
    o = hp.create(ChoiceUnionClass, f=choice_union_asset_yaml_input.filename)

    assert isinstance(o.union_field, OptionTwoClass)
    assert o.union_field.string_field == "foobar"
