# Copyright 2021 MosaicML. All Rights Reserved.

import os
from dataclasses import dataclass
from typing import Optional

import yahp as hp


@dataclass
class SimpleExample(hp.Hparams):
    foo: int = hp.required('foo field')
    bar: float = hp.optional('bar field', default=1.0)
    baz: Optional[str] = hp.optional('baz', default=None)


# load parameters from simple.yaml
hparams = SimpleExample.create(os.path.join(os.path.dirname(__file__), 'simple.yaml'))

print(hparams)
