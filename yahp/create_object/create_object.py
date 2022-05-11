import pathlib
from typing import TYPE_CHECKING, Dict, List, Optional, TextIO, Type, TypeVar, Union

import yahp as hp
from yahp.create_object.create_from_hparams import create_from_hparams

TObject = TypeVar('TObject')

if TYPE_CHECKING:
    from yahp.types import JSON


def create(
    cls: Type[TObject],
    data: Optional[Dict[str, JSON]] = None,
    f: Union[str, TextIO, pathlib.PurePath, None] = None,
    cli_args: Union[List[str], bool] = True,
) -> TObject:
    if not issubclass(cls, hp.Hparams):
        raise NotImplementedError('TODO -- make an hparams class dynamically from cls')
    return create_from_hparams(cls, data=data, f=f, cli_args=cli_args)
