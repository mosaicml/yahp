import textwrap
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any, Dict, NamedTuple

import pytest
import yaml

from hparams import hparams
from hparams.hparams import Hparams
from hparams.types import JSON


class YamlInput(NamedTuple):
    yaml_str: str
    dict_data: Dict[str, Any]
    filename: str


class EnumIntField(IntEnum):
    ONE = 1
    TWO = 2
    THREE = 3


class EnumStringField(Enum):
    MOSAIC = "mosaic"
    PYTORCH_LIGHTNING = "ptl"


# -------------------------------------------------
# Helpers
# -------------------------------------------------
@pytest.fixture
def hparams_tempdir(tmp_path):
    d = tmp_path / "hparams"
    d.mkdir()
    return d


def generate_named_tuple_from_str(hparams_tempdir, input_str: str, filepath: str):
    input_data = yaml.full_load(input_str)
    f = hparams_tempdir / filepath
    f.write_text(input_str)
    out = YamlInput(input_str, input_data, f)
    return out


def generate_named_tuple_from_data(hparams_tempdir, input_data: Dict[str, Any], filepath: str):
    input_str = yaml.dump(input_data)
    f = hparams_tempdir / filepath
    f.write_text(input_str)
    return YamlInput(input_str, input_data, f)


# -------------------------------------------------
# Primitive Hparams
# -------------------------------------------------


@dataclass
class EmptyHparam(Hparams):

    def validate(self):
        super().validate()


@dataclass
class PrimitiveHparam(Hparams):
    intfield: int = hparams.required(doc="int field")
    strfield: str = hparams.required(doc="str field")
    floatfield: float = hparams.required(doc="float field")
    boolfield: bool = hparams.required(doc="bool field")
    enumintfield: EnumIntField = hparams.required(doc="enum int field")
    enumstringfield: EnumStringField = hparams.required(doc="enum int field")
    jsonfield: Dict[str, JSON] = hparams.required(doc="Required json type")

    def validate(self):
        assert isinstance(self.intfield, int)
        assert isinstance(self.strfield, str)
        assert isinstance(self.floatfield, float)
        assert isinstance(self.boolfield, bool)
        assert isinstance(self.enumintfield, EnumIntField)
        assert isinstance(self.enumstringfield, EnumStringField)
        jsonfield_real_value = {
            'empty_item': {},
            'random_item': 1,
            'random_item2': 'two',
            'random_item3': True,
            'random_item4': 0.1,
            'random_subdict': {
                'random_subdict_item5': 12,
                'random_subdict_item6': 1337
            },
            'random_list': [1, 3, 99],
            'random_list_of_dict': [{
                'sub_dict': 12,
                'sub_dict_item': 1
            }, {
                'sub_dict2': 14,
                'sub_dict_item': 43
            }]
        }
        d1 = yaml.dump(self.jsonfield, sort_keys=True)
        d2 = yaml.dump(jsonfield_real_value, sort_keys=True)
        assert d1 == d2
        super().validate()


@pytest.fixture
def primitive_yaml_input(hparams_tempdir) -> YamlInput:
    primitive_hparams_input_str = textwrap.dedent("""
    ---
    intfield: 1
    strfield: hello
    floatfield: 0.5
    boolfield: true
    enumintfield: ONE
    enumstringfield: pytorch_lightning
    jsonfield:
      empty_item: {}
      random_item: 1
      random_item2: two
      random_item3: true
      random_item4: 0.1
      random_subdict:
        random_subdict_item5: 12
        random_subdict_item6: 1337
      random_list:
        - 1
        - 3
        - 99
      random_list_of_dict:
        - sub_dict: 12
          sub_dict_item: 1
        - sub_dict2: 14
          sub_dict_item: 43
    """)
    return generate_named_tuple_from_str(
        hparams_tempdir=hparams_tempdir,
        input_str=primitive_hparams_input_str,
        filepath="simple_hparams.yaml",
    )


@pytest.fixture
def primitive_hparam(primitive_yaml_input: YamlInput):
    return PrimitiveHparam.create_from_dict(primitive_yaml_input.dict_data)


# -------------------------------------------------
# Nested Hparams
# -------------------------------------------------
@dataclass
class NestedHparam(Hparams):
    primitive_hparam: PrimitiveHparam = hparams.required(doc="Primitive Hparams")
    empty_hparam: EmptyHparam = hparams.required(doc="Empty Hparams")

    def validate(self):
        assert isinstance(self.primitive_hparam, PrimitiveHparam)
        self.primitive_hparam.validate()
        super().validate()


@pytest.fixture
def nested_yaml_input(hparams_tempdir, primitive_yaml_input: YamlInput) -> YamlInput:
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data={
            "primitive_hparam": primitive_yaml_input.dict_data,
            "empty_hparam": {}
        },
        filepath="direct_nested.yaml",
    )


@pytest.fixture
def nested_hparams(nested_yaml_input: YamlInput) -> NestedHparam:
    hp = NestedHparam.create_from_dict(nested_yaml_input.dict_data)
    assert isinstance(hp, NestedHparam)
    return hp


@dataclass
class DoubleNestedHparam(Hparams):
    nested_hparams: NestedHparam = hparams.required(doc="Primitive Hparams")
    random_field: int = hparams.required(doc="random int")

    def validate(self):
        assert isinstance(self.random_field, int)
        assert isinstance(self.nested_hparams, NestedHparam)
        self.nested_hparams.validate()
        super().validate()


@pytest.fixture
def double_nested_yaml_input(hparams_tempdir, nested_yaml_input: YamlInput) -> YamlInput:
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data={
            "nested_hparams": nested_yaml_input.dict_data,
            "random_field": 42
        },
        filepath="double_nested.yaml",
    )


@pytest.fixture
def double_nested_hparams(double_nested_yaml_input: YamlInput) -> DoubleNestedHparam:
    hp = DoubleNestedHparam.create_from_dict(double_nested_yaml_input.dict_data)
    assert isinstance(hp, DoubleNestedHparam)
    return hp


# -------------------------------------------------
# Choice Hparams
# -------------------------------------------------
@dataclass
class ChoiceHparamParent(Hparams):
    commonfield: bool = hparams.required(doc="bool common field")

    def validate(self):
        assert isinstance(self.commonfield, bool)
        super().validate()


@dataclass
class ChoiceOneHparam(ChoiceHparamParent):
    intfield: int = hparams.required(doc="int field")

    def validate(self):
        assert isinstance(self.intfield, int)
        super().validate()


@pytest.fixture
def choice_one_yaml_input(hparams_tempdir) -> YamlInput:
    input_str = textwrap.dedent("""
    ---
    commonfield: true
    intfield: 1337
    """)
    return generate_named_tuple_from_str(
        hparams_tempdir=hparams_tempdir,
        input_str=input_str,
        filepath="choice_one.yaml",
    )


@pytest.fixture
def choice_one_hparams(choice_one_yaml_input: YamlInput) -> ChoiceOneHparam:
    hp = ChoiceOneHparam.create_from_dict(choice_one_yaml_input.dict_data)
    assert isinstance(hp, ChoiceOneHparam)
    return hp


# Directly nested subhparam
@dataclass
class ChoiceTwoHparam(ChoiceHparamParent):
    primitive_hparam: PrimitiveHparam = hparams.required(doc="Primitive Hparams")
    boolfield: int = hparams.required(doc="int field")

    def validate(self):
        assert isinstance(self.boolfield, bool)
        assert isinstance(self.primitive_hparam, PrimitiveHparam)
        self.primitive_hparam.validate()
        super().validate()


@pytest.fixture
def choice_two_yaml_input(hparams_tempdir, primitive_yaml_input: YamlInput) -> YamlInput:
    data = {
        "primitive_hparam": primitive_yaml_input.dict_data,
        "commonfield": False,
        "boolfield": False,
    }
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data=data,
        filepath="choice_two.yaml",
    )


@pytest.fixture
def choice_two_hparams(choice_two_yaml_input: YamlInput) -> ChoiceTwoHparam:
    hp = ChoiceTwoHparam.create_from_dict(choice_two_yaml_input.dict_data)
    assert isinstance(hp, ChoiceTwoHparam)
    return hp


# Can choose again other options one or two
@dataclass
class ChoiceThreeHparam(ChoiceHparamParent):
    hparams_registry = {
        "choice": {
            "one": ChoiceOneHparam,
            "two": ChoiceTwoHparam,
        }
    }

    choice: ChoiceHparamParent = hparams.required(doc="choice Hparam field")
    strfield: str = hparams.required(doc="str field")

    def validate(self):
        assert isinstance(self.strfield, str)
        assert isinstance(self.choice, ChoiceHparamParent)
        super().validate()


@pytest.fixture
def choice_three_two_yaml_input(hparams_tempdir, choice_two_yaml_input: YamlInput) -> YamlInput:
    data = {
        "choice": {
            "two": choice_two_yaml_input.dict_data
        },
        "commonfield": False,
        "strfield": "tomatoes",
    }
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data=data,
        filepath="choice_three_two.yaml",
    )


@pytest.fixture
def choice_three_one_yaml_input(hparams_tempdir, choice_one_yaml_input: YamlInput) -> YamlInput:
    data = {
        "choice": {
            "one": choice_one_yaml_input.dict_data
        },
        "commonfield": True,
        "strfield": "potatoes",
    }
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data=data,
        filepath="choice_three_one.yaml",
    )


@pytest.fixture
def choice_three_two_hparam(choice_three_two_yaml_input: YamlInput) -> ChoiceThreeHparam:
    hp = ChoiceThreeHparam.create_from_dict(choice_three_two_yaml_input.dict_data)
    assert isinstance(hp, ChoiceThreeHparam)
    return hp


@pytest.fixture
def choice_three_one_hparam(choice_three_one_yaml_input: YamlInput) -> ChoiceThreeHparam:
    hp = ChoiceThreeHparam.create_from_dict(choice_three_one_yaml_input.dict_data)
    assert isinstance(hp, ChoiceThreeHparam)
    return hp


@dataclass
class ChoiceHparamRoot(Hparams):

    hparams_registry = {
        "choice": {
            "one": ChoiceOneHparam,
            "two": ChoiceTwoHparam,
            "three": ChoiceThreeHparam,
        }
    }

    choice: ChoiceHparamParent = hparams.required(doc="choice Hparam field")

    def validate(self):
        assert isinstance(self.choice, ChoiceHparamParent)
        self.choice.validate()
        super().validate()


@dataclass
class ChoiceOptionalFieldsHparam(Hparams):
    maybe: int = hparams.optional(doc="some optional field", default=0)

    def validate(self):
        assert isinstance(self.maybe, int)
        super().validate()


@dataclass
class OptionalFieldHparam(Hparams):
    hparams_registry = {"choice": {"one": ChoiceOptionalFieldsHparam, "two": ChoiceOptionalFieldsHparam}}

    choice: ChoiceOptionalFieldsHparam = hparams.required(doc="choice Hparam field")

    def validate(self):
        assert isinstance(self.choice, ChoiceOptionalFieldsHparam)
        self.choice.validate()
        super().validate()


@pytest.fixture
def optional_field_empty_object_yaml_input(hparams_tempdir) -> YamlInput:
    data = {"choice": {"one": {"maybe": True}}}
    return generate_named_tuple_from_data(hparams_tempdir=hparams_tempdir,
                                          input_data=data,
                                          filepath="optional_field_empty_object.yaml")
