from dataclasses import dataclass
from io import StringIO
from typing import List

import yahp as hp


@dataclass
class Foo(hp.Hparams):
    baz: List[int] = hp.required(doc='ints')
    bar: List[List[int]] = hp.required(doc='ints')


def test_list_of_lists():
    hp = Foo.create(data={
        'baz': [3, 4],
        'bar': [[1, 2], [3, 4]]
    })

    assert isinstance(hp.baz, list)
    assert isinstance(hp.bar, list)
    assert hp.baz == [3, 4]
    assert hp.bar == [[1, 2], [3, 4]]

def test_list_of_lists_from_yaml():
    yaml = """
baz:
  - 3
  - 4
bar:
  - [1, 2]
  - [3, 4]
"""
    # make it look like a fileobj
    yaml = StringIO(yaml)
    hp = Foo.create(f=yaml)

    assert isinstance(hp.baz, list)
    assert isinstance(hp.bar, list)
    assert hp.baz == [3, 4]
    assert hp.bar == [[1, 2], [3, 4]]