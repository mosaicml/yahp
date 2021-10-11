import os
from abc import ABC
from dataclasses import dataclass
from typing import List, Optional

import yahp as hp


@dataclass
class PersonHprams(hp.Hparams, ABC):
    name: str = hp.required("name")
    age: Optional[int] = hp.optional("age", default=None)


@dataclass
class ChildHparams(PersonHprams):
    parents: List[str] = hp.optional("parents", default_factory=lambda: [])


@dataclass
class AdultHparams(PersonHprams):
    favorite_drink: str = hp.optional("favorite drink", default="Beer")


@dataclass
class RegistryExample(hp.Hparams):
    hparams_registry = {
        "person": {
            "child": ChildHparams,
            "adult": AdultHparams,
        }
    }
    person: PersonHprams = hp.required("person")


child_hparams = RegistryExample.create(os.path.join(os.path.dirname(__file__), "registry_child.yaml"))

print(child_hparams)

print()

adult_hparams = RegistryExample.create(os.path.join(os.path.dirname(__file__), "registry_adult.yaml"))

print(adult_hparams)
