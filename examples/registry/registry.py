# Copyright 2021 MosaicML. All Rights Reserved.

import abc
import dataclasses
import os
from typing import List

import yahp as hp


@dataclasses.dataclass
class Person(hp.Hparams, abc.ABC):
    name: str = hp.required('name')


@dataclasses.dataclass
class AdultHparams(Person):
    num_children: int = hp.optional('num_children', default=0)


@dataclasses.dataclass
class ChildHparams(Person):
    parents: List[str] = hp.required('parents')


@dataclasses.dataclass
class FooHparams(hp.Hparams):
    hparams_registry = {
        'owner':
            {  # key "owner" corresponds to field name "owner" below
                'adult': AdultHparams,
                'child': ChildHparams,
            }
    }
    owner: Person = hp.required('owner')


# [foo_hparams]
foo_hparams = FooHparams.create(os.path.join(os.path.dirname(__file__), 'registry_foo.yaml'))
assert type(foo_hparams.owner) is ChildHparams

print(foo_hparams)


# [bar_dataclass]
@dataclasses.dataclass
class BarHparams(hp.Hparams):
    hparams_registry = {
        'owners':
            {  # key "owners" corresponds to field name "owners" below
                'adult': AdultHparams,
                'child': ChildHparams,
            }
    }
    owners: List[Person] = hp.required('owners')


# [bar_hparams]
bar_hparams = BarHparams.create(os.path.join(os.path.dirname(__file__), 'registry_bar.yaml'))
assert type(bar_hparams.owners[0]) is AdultHparams
assert type(bar_hparams.owners[1]) is ChildHparams

print(bar_hparams)
