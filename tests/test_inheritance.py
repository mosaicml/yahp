import os

import py.path
import yaml

from hparams.inheritance import preprocess_yaml_with_inheritance


def test_yaml_inheritance(tmpdir: py.path.local):
    inheritance_folder = os.path.join(os.path.dirname(__file__), "inheritance")
    input_file = os.path.join(inheritance_folder, "main.yaml")
    output_file = os.path.join(str(tmpdir), "output_yaml.yaml")

    preprocess_yaml_with_inheritance(input_file, output_file)
    expected_output_file = os.path.join(inheritance_folder, "composed.yaml")
    with open(expected_output_file, "r") as f:
        expected_output = yaml.load(f)

    with open(output_file, "r") as f:
        actual_output = yaml.load(f)

    assert actual_output == expected_output
