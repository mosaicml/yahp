import dataclasses
import inspect
import pathlib
from typing import Dict, List, Optional, Sequence, TextIO, Type, TypeVar, Union, cast, get_type_hints

from yahp.hparams import Hparams
from yahp.types import JSON
from yahp.utils.type_helpers import HparamsType, is_none_like

T = TypeVar('T')

_REGISTRY_ATTR_NAME = '_yahp_registry'

_PPV_LIST_ATTR_NAME = '_yahp_ppv_list'

_PARAM_TYPE_OVERRIDE_DICT_ATTR_NAME = '_yahp_param_override_dict'


def create_subclass_registry():
    """Create a registry to track subclasses of this object so they can satisfy parameters of this object's type."""

    def decorator(cls: Type):
        if hasattr(cls, _REGISTRY_ATTR_NAME):
            raise ValueError(f"The YAHP registry for {cls.__qualname__} has already been initialized.")
        setattr(cls, _REGISTRY_ATTR_NAME, {})

        old_init_subclass = cls.__init_subclass__

        @classmethod
        def new_init_subclass(subcls, canonical_name: str, **kwargs):
            registry = getattr(cls, _REGISTRY_ATTR_NAME)
            registry[canonical_name] = subcls

            ppv_list = getattr(cls, _PPV_LIST_ATTR_NAME, [])
            setattr(subcls, _PPV_LIST_ATTR_NAME, ppv_list)

            old_init_subclass(**kwargs)

        cls.__init_subclass__ = new_init_subclass

        return cls

    return decorator


def mark_parent_provided_value(parameter_name: str):
    """Mark a parameter as being provided by """

    def decorator(cls: Type):
        if not hasattr(cls, _PPV_LIST_ATTR_NAME):
            setattr(cls, _PPV_LIST_ATTR_NAME, [])
        ppv_list = getattr(cls, _PPV_LIST_ATTR_NAME)
        ppv_list.append(parameter_name)
        return cls

    return decorator


def override_parameter_type(parameter_name: str, parameter_type: Type):

    def decorator(cls: Type):
        if not hasattr(cls, _PARAM_TYPE_OVERRIDE_DICT_ATTR_NAME):
            setattr(cls, _PARAM_TYPE_OVERRIDE_DICT_ATTR_NAME, {})
        param_type_override_dict = getattr(cls, _PARAM_TYPE_OVERRIDE_DICT_ATTR_NAME)
        param_type_override_dict[parameter_name] = parameter_type
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

    # `get_type_hints` is necessary to resolve annotations at runtime under PEP 563.
    # See https://www.python.org/dev/peps/pep-0563/#resolving-type-hints-at-runtime.
    type_hints = get_type_hints(asset_class.__init__)

    ppv_list = getattr(asset_class, _PPV_LIST_ATTR_NAME, [])
    param_type_override_dict = getattr(asset_class, _PARAM_TYPE_OVERRIDE_DICT_ATTR_NAME, {})

    fields = []
    hparams_registry = {}

    for parameter in parameters:

        field_name = parameter.name
        assert field_name in type_hints
        field_type = type_hints[field_name]

        if field_name in param_type_override_dict:
            field_type = param_type_override_dict[field_name]

        if field_name in ppv_list:
            continue

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

    hp_class = dataclasses.make_dataclass(f'{asset_class.__name__}Hparams', fields=fields, bases=(Hparams,))
    hp_class.hparams_registry = hparams_registry
    hp_class.asset_class = asset_class

    return hp_class


def _initialize_asset(asset_class: Type[T], hparams: Hparams, **kwargs) -> T:

    fields = dataclasses.fields(hparams)
    fields_by_name = {field.name: field for field in fields}

    asset_args = {k: v for k, v in kwargs.items()}

    def _initialize_field(field_name: str):
        if field_name in asset_args:
            # Already initialized this field
            return

        field = fields_by_name[field_name]
        hparam_value = getattr(hparams, field_name)
        if field.metadata['is_nested_class']:
            parsed_field_type = cast(HparamsType, field.metadata['parsed_field_type'])

            ppv_list = getattr(parsed_field_type.type, _PPV_LIST_ATTR_NAME, [])
            ppv = {}
            for ppv_field_name in ppv_list:
                _initialize_field(ppv_field_name)
                ppv[ppv_field_name] = asset_args[ppv_field_name]

            if parsed_field_type.is_optional and is_none_like(hparam_value, allow_list=parsed_field_type.is_list):
                asset_args[field_name] = None
            elif parsed_field_type.is_list:
                assert isinstance(hparam_value, Sequence)
                asset_args[field_name] = [
                    _initialize_asset(hparam_value_item.asset_class, hparam_value_item, **ppv)
                    for hparam_value_item in hparam_value
                ]
            else:
                asset_args[field_name] = _initialize_asset(hparam_value.asset_class, hparam_value, **ppv)
        else:
            asset_args[field_name] = hparam_value

    for field in fields:
        _initialize_field(field.name)

    return asset_class(**asset_args)
