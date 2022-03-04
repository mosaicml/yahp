# Copyright 2021 MosaicML. All Rights Reserved.

import os
from typing import Type

import tests
from yahp import Hparams

SAVE_FIXTURE = False
FIXTURE_PATH = os.path.join(os.path.dirname(tests.__file__), 'fixtures', 'commented_map.yaml')


def test_to_commented_map(kitchen_sink_hparams: Type[Hparams]):
    output = kitchen_sink_hparams.dumps(add_docs=True, interactive=False)

    if SAVE_FIXTURE:
        # helper to easily update the test fixture
        with open(FIXTURE_PATH, 'w+') as f:
            f.write(output)
        assert False, 'Set SAVE_FIXTURE to False'
    with open(FIXTURE_PATH, 'r') as f:
        assert output == f.read()


def test_load_commented_map(kitchen_sink_hparams: Type[Hparams]):
    hparams = kitchen_sink_hparams.create(FIXTURE_PATH,
                                          cli_args=[
                                              '--required_int_field',
                                              '2',
                                              '--required_bool_field',
                                              'false',
                                              '--required_choice',
                                              'one',
                                              '--required_choice.one.commonfield',
                                              'True',
                                              '--required_choice.one.intfield',
                                              '5',
                                              '--required_choice_list',
                                              'one',
                                              '--required_choice_list.one.commonfield',
                                              'True',
                                              '--required_choice_list.one.intfield',
                                              '5',
                                          ])
    hparams.validate()
    assert isinstance(hparams, kitchen_sink_hparams)
