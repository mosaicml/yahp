import os
from typing import Type

import tests
from yahp.yahp import Hparams

SAVE_FIXTURE = False


def test_to_commented_map(kitchen_sink_hparams: Type[Hparams]):
    output = kitchen_sink_hparams.dumps(comment_helptext=True, interactive=False)
    fixture_path = os.path.join(os.path.dirname(tests.__file__), "fixtures", "commented_map.yaml")
    if SAVE_FIXTURE:
        # helper to easily update the test fixture
        with open(fixture_path, "w+") as f:
            f.write(output)
        assert False, "Set SAVE_FIXTURE to False"
    with open(fixture_path) as f:
        assert output == f.read()
