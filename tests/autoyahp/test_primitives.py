import pathlib
from typing import List, Optional

import pytest

import yahp as hp
from tests.yahp_fixtures import YamlInput, generate_named_tuple_from_data


class PrimitivesClass:

    def __init__(
        self,
        bool_field: bool,
        int_field: int,
        float_field: float,
        string_field: str,
    ):
        self.bool_field = bool_field
        self.int_field = int_field
        self.float_field = float_field
        self.string_field = string_field


@pytest.fixture
def primitives_class_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data={
            "bool_field": True,
            "int_field": 50,
            "float_field": 3.14,
            "string_field": "foobar",
        },
        filepath="primitives_class.yaml",
    )


def test_primitives_class_hparams_data(primitives_class_yaml_input: YamlInput):
    o = hp.create(PrimitivesClass, data=primitives_class_yaml_input.dict_data)

    assert o.bool_field == True
    assert o.int_field == 50
    assert o.float_field == 3.14
    assert o.string_field == "foobar"


def test_primitives_class_hparams_file(primitives_class_yaml_input: YamlInput):
    o = hp.create(PrimitivesClass, f=primitives_class_yaml_input.filename)

    assert o.bool_field == True
    assert o.int_field == 50
    assert o.float_field == 3.14
    assert o.string_field == "foobar"


class ListPrimitivesClass:

    def __init__(
        self,
        bools_field: List[bool],
        ints_field: List[int],
        floats_field: List[float],
        strings_field: List[str],
    ):
        self.bools_field = bools_field
        self.ints_field = ints_field
        self.floats_field = floats_field
        self.strings_field = strings_field


@pytest.fixture
def list_primitives_class_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data={
            "bools_field": [True, False, True],
            "ints_field": [1, 2, 3],
            "floats_field": [3.14, 4.67],
            "strings_field": ["abc", "def"],
        },
        filepath="list_primitives_class.yaml",
    )


def test_list_primitives_class_hparams_data(list_primitives_class_yaml_input: YamlInput):
    o = hp.create(ListPrimitivesClass, data=list_primitives_class_yaml_input.dict_data)

    assert o.bools_field == [True, False, True]
    assert o.ints_field == [1, 2, 3]
    assert o.floats_field == [3.14, 4.67]
    assert o.strings_field == ["abc", "def"]


def test_list_primitives_class_hparams_file(list_primitives_class_yaml_input: YamlInput):
    o = hp.create(ListPrimitivesClass, f=list_primitives_class_yaml_input.filename)

    assert o.bools_field == [True, False, True]
    assert o.ints_field == [1, 2, 3]
    assert o.floats_field == [3.14, 4.67]
    assert o.strings_field == ["abc", "def"]


class OptionalPrimitivesClass:

    def __init__(
        self,
        bool_field: Optional[bool],
        ints_field: Optional[List[int]],
        float_field: float = 3.14,
    ):
        self.bool_field = bool_field
        self.ints_field = ints_field
        self.float_field = float_field


@pytest.fixture
def optional_primitives_class_empty_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data={},
        filepath="optional_primitives_class_empty.yaml",
    )


@pytest.fixture
def optional_primitives_class_filled_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data={
            "bool_field": False,
            "ints_field": [1, 2, 3],
            "float_field": 2.718,
        },
        filepath="optional_primitives_class_filled.yaml",
    )


def test_list_primitives_class_empty_hparams_data(optional_primitives_class_empty_yaml_input: YamlInput):
    o = hp.create(OptionalPrimitivesClass, data=optional_primitives_class_empty_yaml_input.dict_data)

    assert o.bool_field == None
    assert o.ints_field == None
    assert o.float_field == 3.14


def test_list_primitives_class_empty_hparams_file(optional_primitives_class_empty_yaml_input: YamlInput):
    o = hp.create(OptionalPrimitivesClass, f=optional_primitives_class_empty_yaml_input.filename)

    assert o.bool_field == None
    assert o.ints_field == None
    assert o.float_field == 3.14


def test_list_primitives_class_filled_hparams_data(optional_primitives_class_filled_yaml_input: YamlInput):
    o = hp.create(OptionalPrimitivesClass, data=optional_primitives_class_filled_yaml_input.dict_data)

    assert o.bool_field == False
    assert o.ints_field == [1, 2, 3]
    assert o.float_field == 2.718


def test_list_primitives_class_filled_hparams_file(optional_primitives_class_filled_yaml_input: YamlInput):
    o = hp.create(OptionalPrimitivesClass, f=optional_primitives_class_filled_yaml_input.filename)

    assert o.bool_field == False
    assert o.ints_field == [1, 2, 3]
    assert o.float_field == 2.718
