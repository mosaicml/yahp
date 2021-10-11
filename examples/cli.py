import os
from dataclasses import dataclass
from typing import Optional

import yahp as hp


@dataclass
class CLIExample(hp.Hparams):
    foo: int = hp.required("foo field")
    bar: float = hp.optional("bar field", default=1.0)
    baz: Optional[str] = hp.optional("baz", default=None)


# load parameters from cli.yaml
# NOTE: cli.yaml does NOT define `foo`, so it will need to be specified
# on the command line.
# Try running: examples/cli.py --help
hparams = CLIExample.create(os.path.join(os.path.dirname(__file__), "cli.yaml"))

print(hparams)
