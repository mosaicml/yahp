# Copyright 2021 MosaicML. All Rights Reserved.

import pathlib
import textwrap
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any, Dict, List, NamedTuple, Optional, Union

import pytest
import yaml

import yahp as hp
from yahp.types import JSON


class YamlInput(NamedTuple):
    yaml_str: str
    dict_data: Dict[str, Any]
    filename: str


class EnumIntField(IntEnum):
    ONE = 1
    TWO = 2
    THREE = 3


class EnumStringField(Enum):
    MOSAIC = 'mosaic'
    PYTORCH_LIGHTNING = 'ptl'


# -------------------------------------------------
# Helpers
# -------------------------------------------------
@pytest.fixture
def hparams_tempdir(tmp_path: pathlib.Path):
    d = tmp_path / 'hparams'
    d.mkdir()
    return d


def generate_named_tuple_from_str(hparams_tempdir: pathlib.Path, input_str: str, filepath: str):
    input_data = yaml.full_load(input_str)
    f = hparams_tempdir / filepath
    f.write_text(input_str)
    out = YamlInput(input_str, input_data, str(f))
    return out


def generate_named_tuple_from_data(hparams_tempdir: pathlib.Path, input_data: Dict[str, Any], filepath: str):
    input_str = yaml.dump(input_data)
    f = hparams_tempdir / filepath
    f.write_text(input_str)
    return YamlInput(input_str, input_data, str(f))


# -------------------------------------------------
# Primitive Hparams
# -------------------------------------------------


@dataclass
class EmptyHparam(hp.Hparams):

    def validate(self):
        super().validate()


@dataclass
class PrimitiveHparam(hp.Hparams):
    intfield: int = hp.required(doc='int field')
    strfield: str = hp.required(doc='str field')
    floatfield: float = hp.required(doc='float field')
    boolfield: bool = hp.required(doc='bool field')
    enumintfield: EnumIntField = hp.required(doc='enum int field')
    enumstringfield: EnumStringField = hp.required(doc='enum int field')
    jsonfield: Dict[str, JSON] = hp.required(doc='Required json type')

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
def primitive_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
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
        filepath='simple_hparams.yaml',
    )


@pytest.fixture
def primitive_hparam(primitive_yaml_input: YamlInput):
    return PrimitiveHparam.create(data=primitive_yaml_input.dict_data)


# -------------------------------------------------
# Nested Hparams
# -------------------------------------------------
@dataclass
class NestedHparam(hp.Hparams):
    primitive_hparam: PrimitiveHparam = hp.required(doc='Primitive Hparams')
    empty_hparam: EmptyHparam = hp.required(doc='Empty Hparams')

    def validate(self):
        assert isinstance(self.primitive_hparam, PrimitiveHparam)
        self.primitive_hparam.validate()
        super().validate()


@pytest.fixture
def nested_yaml_input(hparams_tempdir: pathlib.Path, primitive_yaml_input: YamlInput) -> YamlInput:
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data={
            'primitive_hparam': primitive_yaml_input.dict_data,
            'empty_hparam': {}
        },
        filepath='direct_nested.yaml',
    )


@pytest.fixture
def nested_hparams(nested_yaml_input: YamlInput) -> NestedHparam:
    hp = NestedHparam.create(data=nested_yaml_input.dict_data)
    assert isinstance(hp, NestedHparam)
    return hp


@dataclass
class DoubleNestedHparam(hp.Hparams):
    nested_hparams: NestedHparam = hp.required(doc='Primitive Hparams')
    random_field: int = hp.required(doc='random int')

    def validate(self):
        assert isinstance(self.random_field, int)
        assert isinstance(self.nested_hparams, NestedHparam)
        self.nested_hparams.validate()
        super().validate()


@pytest.fixture
def double_nested_yaml_input(hparams_tempdir: pathlib.Path, nested_yaml_input: YamlInput) -> YamlInput:
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data={
            'nested_hparams': nested_yaml_input.dict_data,
            'random_field': 42
        },
        filepath='double_nested.yaml',
    )


@pytest.fixture
def double_nested_hparams(double_nested_yaml_input: YamlInput) -> DoubleNestedHparam:
    hp = DoubleNestedHparam.create(data=double_nested_yaml_input.dict_data)
    assert isinstance(hp, DoubleNestedHparam)
    return hp


# -------------------------------------------------
# Choice Hparams
# -------------------------------------------------
@dataclass
class ChoiceHparamParent(hp.Hparams):
    commonfield: bool = hp.required(doc='bool common field')

    def validate(self):
        assert isinstance(self.commonfield, bool)
        super().validate()


@dataclass
class ChoiceOneHparam(ChoiceHparamParent):
    intfield: int = hp.required(doc='int field')

    def validate(self):
        assert isinstance(self.intfield, int)
        super().validate()


@pytest.fixture
def choice_one_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    input_str = textwrap.dedent("""
    ---
    commonfield: true
    intfield: 1337
    """)
    return generate_named_tuple_from_str(
        hparams_tempdir=hparams_tempdir,
        input_str=input_str,
        filepath='choice_one.yaml',
    )


@pytest.fixture
def choice_one_hparams(choice_one_yaml_input: YamlInput) -> ChoiceOneHparam:
    hp = ChoiceOneHparam.create(data=choice_one_yaml_input.dict_data)
    assert isinstance(hp, ChoiceOneHparam)
    return hp


# Directly nested subhparam
@dataclass
class ChoiceTwoHparam(ChoiceHparamParent):
    primitive_hparam: PrimitiveHparam = hp.required(doc='Primitive Hparams')
    boolfield: int = hp.required(doc='int field')

    def validate(self):
        assert isinstance(self.boolfield, bool)
        assert isinstance(self.primitive_hparam, PrimitiveHparam)
        self.primitive_hparam.validate()
        super().validate()


@pytest.fixture
def choice_two_yaml_input(hparams_tempdir: pathlib.Path, primitive_yaml_input: YamlInput) -> YamlInput:
    data = {
        'primitive_hparam': primitive_yaml_input.dict_data,
        'commonfield': False,
        'boolfield': False,
    }
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data=data,
        filepath='choice_two.yaml',
    )


@pytest.fixture
def choice_two_hparams(choice_two_yaml_input: YamlInput) -> ChoiceTwoHparam:
    hp = ChoiceTwoHparam.create(data=choice_two_yaml_input.dict_data)
    assert isinstance(hp, ChoiceTwoHparam)
    return hp


# Can choose again other options one or two
@dataclass
class ChoiceThreeHparam(ChoiceHparamParent):
    hparams_registry = {
        'choice': {
            'one': ChoiceOneHparam,
            'two': ChoiceTwoHparam,
        }
    }

    choice: ChoiceHparamParent = hp.required(doc='choice Hparam field')
    strfield: str = hp.required(doc='str field')

    def validate(self):
        assert isinstance(self.strfield, str)
        assert isinstance(self.choice, ChoiceHparamParent)
        super().validate()


@pytest.fixture
def choice_three_two_yaml_input(hparams_tempdir: pathlib.Path, choice_two_yaml_input: YamlInput) -> YamlInput:
    data = {
        'choice': {
            'two': choice_two_yaml_input.dict_data
        },
        'commonfield': False,
        'strfield': 'tomatoes',
    }
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data=data,
        filepath='choice_three_two.yaml',
    )


@pytest.fixture
def choice_three_one_yaml_input(hparams_tempdir: pathlib.Path, choice_one_yaml_input: YamlInput) -> YamlInput:
    data = {
        'choice': {
            'one': choice_one_yaml_input.dict_data
        },
        'commonfield': True,
        'strfield': 'potatoes',
    }
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data=data,
        filepath='choice_three_one.yaml',
    )


@pytest.fixture
def choice_three_two_hparam(choice_three_two_yaml_input: YamlInput) -> ChoiceThreeHparam:
    hp = ChoiceThreeHparam.create(data=choice_three_two_yaml_input.dict_data)
    assert isinstance(hp, ChoiceThreeHparam)
    return hp


@pytest.fixture
def choice_three_one_hparam(choice_three_one_yaml_input: YamlInput) -> ChoiceThreeHparam:
    hp = ChoiceThreeHparam.create(data=choice_three_one_yaml_input.dict_data)
    assert isinstance(hp, ChoiceThreeHparam)
    return hp


@dataclass
class ChoiceHparamRoot(hp.Hparams):

    hparams_registry = {
        'choice': {
            'one': ChoiceOneHparam,
            'two': ChoiceTwoHparam,
            'three': ChoiceThreeHparam,
        }
    }

    choice: ChoiceHparamParent = hp.required(doc='choice Hparam field')

    def validate(self):
        assert isinstance(self.choice, ChoiceHparamParent)
        self.choice.validate()
        super().validate()


@dataclass
class ChoiceOptionalFieldsHparam(hp.Hparams):
    maybe: int = hp.optional(doc='some optional field', default=0)

    def validate(self):
        assert isinstance(self.maybe, int)
        super().validate()


@dataclass
class OptionalHparamsField(hp.Hparams):
    optional_hparams: Optional[hp.Hparams] = hp.optional('optional hparams field', default=None)


@dataclass
class OptionalFieldHparam(hp.Hparams):
    hparams_registry = {'choice': {'one': ChoiceOptionalFieldsHparam}}

    choice: ChoiceOptionalFieldsHparam = hp.required(doc='choice Hparam field')

    def validate(self):
        assert isinstance(self.choice, ChoiceOptionalFieldsHparam)
        self.choice.validate()
        super().validate()


@pytest.fixture
def optional_field_empty_object_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    data = {'choice': {'one': {}}}
    return generate_named_tuple_from_data(hparams_tempdir=hparams_tempdir,
                                          input_data=data,
                                          filepath='optional_field_empty_object.yaml')


@pytest.fixture
def optional_field_null_object_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    data = {'choice': {'one': None}}
    return generate_named_tuple_from_data(hparams_tempdir=hparams_tempdir,
                                          input_data=data,
                                          filepath='optional_field_null_object.yaml')


@dataclass
class OptionalBooleansHparam(hp.Hparams):
    default_false: bool = hp.optional(doc='defaults to false', default=False)
    default_true: bool = hp.optional(doc='defaults to true', default=True)


@dataclass
class ListHparam(hp.Hparams):
    list_of_str: List[str] = hp.optional(doc='defaults to empty list', default_factory=list)
    list_of_int: List[int] = hp.optional(doc='defaults to empty list', default_factory=list)
    list_of_bool: List[bool] = hp.optional(doc='defaults to empty list', default_factory=list)


@pytest.fixture
def empty_object_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    return generate_named_tuple_from_data(hparams_tempdir=hparams_tempdir, input_data={}, filepath='empty_object.yaml')


class DummyEnum(IntEnum):
    RED = 1
    GREEN = 2
    blue = 3


@dataclass
class FloatToBoolFixture(hp.Hparams):
    float_field: float = hp.optional(doc='please autoconvert to float', default=1)


@dataclass
class KitchenSinkHparams(hp.Hparams):
    hparams_registry = {
        fname: {
            'one': ChoiceOneHparam,
            'two': ChoiceTwoHparam,
            'three': ChoiceThreeHparam,
        } for fname in [
            'required_choice',
            'nullable_required_choice',
            'optional_choice_default_not_none',
            'optional_choice_default_none',
            'required_choice_list',
            'nullable_required_choice_list',
            'optional_choice_default_not_none_list',
            'optional_choice_default_none_list',
        ]
    }

    required_int_field: int = hp.required('required_int_field')
    nullable_required_int_field: Optional[int] = hp.required('nullable_required_int_field')

    required_bool_field: bool = hp.required('required_bool_field')
    nullable_required_bool_field: Optional[bool] = hp.required('nullable_required_bool_field')

    required_enum_field_list: List[DummyEnum] = hp.required('required_enum_field with default')
    required_enum_field_with_default: DummyEnum = hp.required('required_enum_field', template_default=DummyEnum.GREEN)
    nullable_required_enum_field: Optional[DummyEnum] = hp.required('nullable_required_enum_field',
                                                                    template_default=None)

    required_union_bool_str_field: Union[bool, str] = hp.required('required_union_bool_str_field',
                                                                  template_default='hi')
    nullable_required_union_bool_str_field: Optional[Union[bool,
                                                           str]] = hp.required('nullable_required_union_bool_str_field',
                                                                               template_default=None)

    required_int_list_field: List[int] = hp.required('required_list_int_field', template_default=[2])
    nullable_required_list_int_field: Optional[List[int]] = hp.required('nullable_required_list_int_field',
                                                                        template_default=[3])

    nullable_required_list_union_bool_str_field: Optional[List[Union[bool, str]]] = hp.required(
        'nullable_required_list_union_bool_str_field')
    required_list_union_bool_str_field: List[Union[bool, str]] = hp.required('required_list_union_bool_str_field',
                                                                             template_default=[True, 'hello'])

    required_subhparams_field: OptionalBooleansHparam = hp.required('required_subhparams_field',
                                                                    template_default=OptionalBooleansHparam(True, True))
    nullable_required_subhparams_field: Optional[OptionalBooleansHparam] = hp.required(
        'nullable_required_subhparams_field')

    required_subhparams_field_list: List[OptionalBooleansHparam] = hp.required(
        'required_subhparams_field', template_default=[OptionalBooleansHparam(True, True)])
    nullable_required_subhparams_field_list: Optional[List[OptionalBooleansHparam]] = hp.required(
        'nullable_required_subhparams_field')

    required_choice: ChoiceHparamParent = hp.required(doc='choice Hparam field')
    nullable_required_choice: Optional[ChoiceHparamParent] = hp.required(doc='choice Hparam field',
                                                                         template_default=ChoiceOneHparam(True, 0))

    required_choice_list: List[ChoiceHparamParent] = hp.required(doc='choice Hparam field')
    nullable_required_choice_list: Optional[List[ChoiceHparamParent]] = hp.required(
        doc='choice Hparam field', template_default=[ChoiceOneHparam(True, 0)])

    optional_float_field_default_1: Optional[float] = hp.optional('optional float field default 1', default=1)
    optional_float_field_default_none: Optional[float] = hp.optional('optional float field default None', default=None)

    optional_bool_field_default_true: Optional[bool] = hp.optional('optional bool field default True', default=True)
    optional_bool_field_default_none: Optional[bool] = hp.optional('optional bool field default None', default=None)

    optional_enum_field_default_red: Optional[DummyEnum] = hp.optional('optional enum field default red', default='red')
    optional_enum_field_default_none: Optional[DummyEnum] = hp.optional('optional enum field default None',
                                                                        default=None)

    optional_union_bool_str_field_default_true: Optional[Union[bool, str]] = hp.optional(
        'optional union_bool_str field default True', default=True)
    optional_union_bool_str_field_default_hello: Optional[Union[bool, str]] = hp.optional(
        'optional union_bool_str field default hello', default='hello')
    optional_union_bool_str_field_default_none: Optional[Union[bool, str]] = hp.optional(
        'optional union_bool_str field default None', default=None)

    optional_list_int_field_default_1: Optional[List[int]] = hp.optional('optional list_int field default 1',
                                                                         default_factory=lambda: [1])
    optional_list_int_field_default_none: Optional[List[int]] = hp.optional('optional list_int field default None',
                                                                            default=None)

    optional_list_union_bool_str_field_default_hello: List[Union[bool, str]] = hp.optional(
        'optional list_union_bool_str field default hello', default_factory=lambda: ['hello'])
    optional_list_union_bool_str_field_default_none: Optional[List[Union[bool, str]]] = hp.optional(
        'optional list_union_bool_str field default None', default=None)
    optional_list_union_bool_str_field_default_true: Optional[List[Union[bool, str]]] = hp.optional(
        'optional list_union_bool_str field default True', default_factory=lambda: [True])

    optional_subhparams_field_default_not_none: OptionalBooleansHparam = hp.optional(
        'optional subhparams field default not none', default=OptionalBooleansHparam())
    optional_subhparams_field_default_none: Optional[OptionalBooleansHparam] = hp.optional(
        'optional subhparams field default None', default=None)

    optional_choice_default_not_none: ChoiceHparamParent = hp.optional(
        doc='choice Hparam field', default_factory=lambda: ChoiceOneHparam(False, 0))
    optional_choice_default_none: Optional[ChoiceHparamParent] = hp.optional(doc='choice Hparam field', default=None)

    optional_subhparams_field_default_not_none_list: List[OptionalBooleansHparam] = hp.optional(
        'optional subhparams field default not none', default_factory=lambda: [OptionalBooleansHparam()])
    optional_subhparams_field_default_none_list: Optional[List[OptionalBooleansHparam]] = hp.optional(
        'optional subhparams field default None', default=None)

    optional_choice_default_not_none_list: List[ChoiceHparamParent] = hp.optional(
        doc='choice Hparam field', default_factory=lambda: [ChoiceOneHparam(False, 0)])
    optional_choice_default_none_list: Optional[List[ChoiceHparamParent]] = hp.optional(doc='choice Hparam field',
                                                                                        default=None)


@pytest.fixture
def kitchen_sink_hparams():
    return KitchenSinkHparams


@dataclass
class OptionalRequiredChildHparam(hp.Hparams):
    required_field: int = hp.required(doc='required field')


@dataclass
class OptionalRequiredParentHparam(hp.Hparams):
    optional_child: Optional[OptionalRequiredChildHparam] = hp.optional(doc='optional subhparam', default=None)


@pytest.fixture
def optional_required_missing_optional_yaml_input(hparams_tempdir) -> YamlInput:
    data = {}
    return generate_named_tuple_from_data(hparams_tempdir=hparams_tempdir,
                                          input_data=data,
                                          filepath='optional_required_missing_optional.yaml')


@pytest.fixture
def optional_required_missing_required_yaml_input(hparams_tempdir) -> YamlInput:
    data = {'optional_child': {}}
    return generate_named_tuple_from_data(hparams_tempdir=hparams_tempdir,
                                          input_data=data,
                                          filepath='optional_required_missing_required.yaml')


@pytest.fixture
def optional_required_yaml_input(hparams_tempdir) -> YamlInput:
    data = {'optional_child': {'required_field': 5}}
    return generate_named_tuple_from_data(hparams_tempdir=hparams_tempdir,
                                          input_data=data,
                                          filepath='optional_required.yaml')
