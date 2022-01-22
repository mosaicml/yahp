import dataclasses
import inspect
import pathlib
from typing import Dict, List, Optional, Sequence, TextIO, Type, TypeVar, Union, cast

from yahp.hparams import Hparams
from yahp.types import JSON
from yahp.utils.type_helpers import HparamsType, is_none_like

T = TypeVar('T')

_REGISTRY_ATTR_NAME = '_yahp_registry'


def create_subclass_registry():

    def decorator(cls: Type):
        setattr(cls, _REGISTRY_ATTR_NAME, {})
        return cls

    return decorator


def register_subclass(supercls: Type, canonical_name: str):

    def decorator(cls: Type):
        if not hasattr(supercls, _REGISTRY_ATTR_NAME):
            raise ValueError(f"The YAHP registry of {supercls.__qualname__} has not be initialized.")
        registry = getattr(supercls, _REGISTRY_ATTR_NAME)
        registry[canonical_name] = cls
        return cls

    return decorator


def create(
    asset_class: Type[T],
    data: Optional[Dict[str, JSON]] = None,
    f: Union[str, TextIO, pathlib.PurePath, None] = None,
    cli_args: Union[List[str], bool] = True,
) -> T:
    hp_class = _construct_hparams_class(asset_class)
    hparams = hp_class.create(data=data, f=f, cli_args=cli_args)
    asset = _initialize_asset(asset_class, hparams)
    return asset


def _construct_hparams_class(asset_class: Type) -> Type[Hparams]:

    assert inspect.isclass(asset_class)

    signature = inspect.signature(asset_class)
    parameters = signature.parameters.values()

    fields = []
    hparams_registry = {}

    for parameter in parameters:

        field_name = parameter.name
        field_type = parameter.annotation

        if field_type == inspect.Parameter.empty:
            raise TypeError(
                f"Cannot use YAHP to initialize {asset_class.__qualname__} because parameter {field_name} is untyped.")

        if parameter.kind in [inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.VAR_POSITIONAL]:
            raise TypeError(
                f"Cannot use YAHP to initialize {asset_class.__qualname__} because parameter {field_name} is positional-only."
            )

        default_value = dataclasses.MISSING
        if parameter.default != inspect.Parameter.empty:
            default_value = parameter.default

        parsed_field_type = HparamsType(field_type, allow_classes=True)

        if parsed_field_type.is_primitive:
            if parsed_field_type.is_optional and default_value == dataclasses.MISSING:
                default_value = None
            fields.append((field_name, field_type,
                           dataclasses.field(default=default_value,
                                             metadata={
                                                 'is_nested_class': False,
                                                 'parsed_field_type': parsed_field_type,
                                                 'doc': 'foo'
                                             })))
        else:
            if hasattr(parsed_field_type.type, _REGISTRY_ATTR_NAME):
                registry = getattr(parsed_field_type.type, _REGISTRY_ATTR_NAME)
                hparams_registry[field_name] = {k: _construct_hparams_class(v) for k, v in registry.items()}
                nested_field_type = dataclasses.make_dataclass(f'{field_name}Hparams', fields=(), bases=(Hparams,))
            else:
                nested_field_type = _construct_hparams_class(parsed_field_type.type)
            if parsed_field_type.is_list:
                nested_field_type = List[nested_field_type]
            if parsed_field_type.is_optional:
                nested_field_type = Optional[nested_field_type]
            fields.append((
                field_name,
                nested_field_type,
                dataclasses.field(
                    # Providing a default value for a nested Hparam is almost certainly a
                    # bug in the user's code, but we'll ignore this to stay consistent with
                    # non-YAHP initialization.
                    default=default_value,
                    metadata={
                        'is_nested_class': True,
                        'parsed_field_type': parsed_field_type,
                        'doc': 'foo'
                    })))

    # Just like for normal functions, default parameters must follow required ones. We could get
    # around this by using kw_only=True in the make_dataclass function, but this is only available
    # in Python 3.10+.
    optional_fields = [field for field in fields if field[2].default != dataclasses.MISSING]
    required_fields = [field for field in fields if field not in optional_fields]
    fields = required_fields + optional_fields

    print(fields)

    hp_class = dataclasses.make_dataclass(f'{asset_class.__name__}Hparams', fields=fields, bases=(Hparams,))
    hp_class.hparams_registry = hparams_registry
    hp_class.asset_class = asset_class

    return hp_class


def _initialize_asset(asset_class: Type[T], hparams: Hparams) -> T:
    args = {}
    for field in dataclasses.fields(hparams):
        hparam_value = getattr(hparams, field.name)
        if field.metadata['is_nested_class']:
            parsed_field_type = cast(HparamsType, field.metadata['parsed_field_type'])
            if parsed_field_type.is_optional and is_none_like(hparam_value, allow_list=parsed_field_type.is_list):
                args[field.name] = None
            elif parsed_field_type.is_list:
                assert isinstance(hparam_value, Sequence)
                args[field.name] = [
                    _initialize_asset(hparam_value_item.asset_class, hparam_value_item)
                    for hparam_value_item in hparam_value
                ]
            else:
                args[field.name] = _initialize_asset(hparam_value.asset_class, hparam_value)
        else:
            args[field.name] = hparam_value

    return asset_class(**args)
