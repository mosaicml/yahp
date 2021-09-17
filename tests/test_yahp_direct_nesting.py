from tests.yahp_fixtures import DoubleNestedHparam, NestedHparam, YamlInput


def test_direct_nested_create_from_dict(nested_yaml_input: YamlInput):
    NestedHparam.create_from_dict(nested_yaml_input.dict_data)


def test_direct_nested_create_from_file(nested_yaml_input: YamlInput):
    NestedHparam.create(filepath=nested_yaml_input.filename)


def test_direct_nested_field_types(nested_hparams: NestedHparam):
    nested_hparams.validate()


def test_double_nested_create_from_dict(double_nested_yaml_input: YamlInput):
    DoubleNestedHparam.create_from_dict(double_nested_yaml_input.dict_data)


def test_double_nested_create_from_file(double_nested_yaml_input: YamlInput):
    DoubleNestedHparam.create(filepath=double_nested_yaml_input.filename)


def test_double_nested_field_types(double_nested_hparams: DoubleNestedHparam):
    double_nested_hparams.validate()
