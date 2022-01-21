import pathlib
from typing import List, Optional

import pytest

from tests.yahp_fixtures import YamlInput, generate_named_tuple_from_data
from yahp.autoinit import autoinit


class Choose:
    pass


class OptionOne(Choose):

    def __init__(self, field_one: int):
        self.field_one = field_one


class OptionTwo(Choose):

    def __init__(self, field_two: int):
        self.field_two = field_two


Choose.registry = {'option_one': OptionOne, 'option_two': OptionTwo}


class InnerClass:

    def __init__(self, int_field: int):
        self.int_field = int_field


class SimpleClass:

    def __init__(
        self,
        *,
        b: bool,
        x: int,
        y: float = 3.14,
        z: str,
        xs: List[int],
        inner: InnerClass,
        inners: List[InnerClass],
        inners2: List[InnerClass],
        inners3: Optional[List[InnerClass]],
        choose: Choose,
        chooses: List[Choose],
        chooses2: Optional[List[Choose]],
    ):
        self.b = b
        self.x = x
        self.y = y
        self.z = z
        self.xs = xs
        self.inner = inner
        self.inners = inners
        self.inners2 = inners2
        self.inners3 = inners3
        self.choose = choose
        self.chooses = chooses
        self.chooses2 = chooses2


@pytest.fixture
def simple_class_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data={
            "b": True,
            "x": 50,
            # "y": 3.14,
            "z": "foobar",
            "xs": [1, 2, 3],
            "inner": {
                "int_field": 7
            },
            "inners": {
                "a": {
                    "int_field": 1
                },
                "b": {
                    "int_field": 2
                }
            },
            "choose": {
                "option_one": {
                    "field_one": 5
                }
            },
            "chooses": {
                "option_one": {
                    "field_one": 5
                },
                "option_two": {
                    "field_two": 5
                }
            },
        },
        filepath="simple_class.yaml",
    )


def test_simple_class_hparams_data(simple_class_yaml_input: YamlInput):
    o = autoinit(SimpleClass, data=simple_class_yaml_input.dict_data)

    print(vars(o))

    assert o.b == True
    assert o.x == 50
    assert o.y == 3.14
    assert o.z == "foobar"

    assert o.xs == [1, 2, 3]

    assert isinstance(o.inner, InnerClass)

    assert o.inner.int_field == 7

    assert False
