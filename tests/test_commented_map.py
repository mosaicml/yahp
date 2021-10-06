import os
from typing import Type

import tests
from yahp.yahp import Hparams


def test_to_commented_map(kitchen_sink_hparams: Type[Hparams]):
    output = kitchen_sink_hparams.dumps(comment_helptext=True, interactive=False)
    # with open("hparams.yaml", "w+") as f:
    #     f.write(output)
    with open(os.path.join(os.path.dirname(tests.__file__), "fixtures", "commented_map.yaml")) as f:
        assert output == f.read()
