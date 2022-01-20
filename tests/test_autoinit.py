
import pytest
import yaml
import pathlib

from tests.yahp_fixtures import YamlInput
from yahp.tests.yahp_fixtures import generate_named_tuple_from_data

class SimpleClass:
    
    def __init__(self, x: int):
        pass

@pytest.fixture
def simple_class_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    return generate_named_tuple_from_data(
        hparams_tempdir=hparams_tempdir,
        input_data={
            "x": 50,
        },
        filepath="simple_class.yaml",
    )

def test_simple_class_hparams_data(simple_class_yaml_input):
    