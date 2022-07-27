# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

import argparse
import json
import logging
import pathlib
import textwrap
import warnings
from abc import ABC
from dataclasses import dataclass, fields
from enum import Enum
from io import StringIO, TextIOWrapper
from typing import (TYPE_CHECKING, Any, Callable, Dict, List, Optional, TextIO, Type, TypeVar, Union, cast,
                    get_type_hints)

import jsonschema
import yaml

from yahp.utils import type_helpers
from yahp.utils.iter_helpers import list_to_deduplicated_dict
from yahp.utils.json_schema_helpers import get_registry_json_schema, get_type_json_schema

if TYPE_CHECKING:
    from yahp.types import JSON

# This is for ruamel.yaml not importing properly in conda
try:
    from ruamel_yaml import YAML  # type: ignore
except ImportError as e:
    from ruamel.yaml import YAML  # type: ignore

logger = logging.getLogger(__name__)

TDefault = TypeVar('TDefault')
THparams = TypeVar('THparams', bound='Hparams')


@dataclass
class Hparams(ABC):
    """
    A collection of hyperparameters with names, types, values, and
    documentation.

    Extends :class:`dataclasses.Dataclass`.

    Attributes:
        hparams_registry (Dict[str, Dict[str, Type[Hparams]]]):
            This registry maps field names (correspond to abstract types)
            to the concrete classes that they could be.

            See the :ref:`Registry Example<Registry Example>` for a walkthrough on how
            the registry works.
    """

    # note: hparams_registry cannot be typed the normal way -- dataclass reads the type annotations
    # and would treat it like an instance variable. Instead, using the python2-style annotations
    hparams_registry = None  # type: Optional[Dict[str, Dict[str, Union[Callable[..., Any], Type["Hparams"]]]]]

    @classmethod
    def validate_keys(cls,
                      keys: List[str],
                      *,
                      allow_missing_keys: bool = False,
                      allow_extra_keys: bool = False) -> None:
        """
        Validates that ``keys`` matches the fields of the :class:`Hparams`.

        Args:
            keys (List[str]): Keys to validate.
            allow_missing_keys (bool, optional):
                Whether to ignore fields that do not have default values
                and are also not specified in ``keys``. Defaults to False.
            allow_extra_keys (bool, optional):
                Whether to allow extra members of ``keys``
                that are not present in the :class:`Hparams`.
                Defaults to False.

        Raises:
            ValueError: Raised if there are missing or extra keys.
        """
        keys_in_yaml = set(keys)
        keys_in_class = set([f.name for f in fields(cls) if f.init])
        required_keys_in_class = set(f.name for f in fields(cls) if f.init and type_helpers.is_field_required(f))

        extra_keys = list(keys_in_yaml - keys_in_class)
        missing_keys = list(required_keys_in_class - keys_in_yaml)

        if not allow_missing_keys and len(missing_keys) > 0:
            raise ValueError(f'Required keys missing in {cls.__name__}', missing_keys)

        if not allow_extra_keys and len(extra_keys) > 0:
            raise ValueError(f'Unexpected keys in {cls.__name__}: ', extra_keys)

    @classmethod
    def create(
        cls: Type[THparams],
        f: Union[str, None, TextIO, pathlib.PurePath] = None,
        data: Optional[Dict[str, JSON]] = None,
        cli_args: Union[List[str], bool] = True,
    ) -> THparams:
        """Create a instance of :class:`Hparams`.

        Args:
            f (Union[str, None, TextIO, pathlib.PurePath], optional):
                If specified, load values from a YAML file.
                Can be either a filepath or file-like object.
                Cannot be specified with ``data``.
            data (Optional[Dict[str, JSON]], optional):
                If specified, uses this dictionary for instantiating
                the :class:`Hparams`. Cannot be specified with ``f``.
            cli_args (Union[List[str], bool], optional):
                CLI argument overrides.
                If True (the default), load CLI arguments from `sys.argv`.
                If False, then do not use any CLI arguments.

        Returns:
            Hparams: An instance of the class.
        """
        from yahp.create_object.create_object import create
        return create(cls, data=data, f=f, cli_args=cli_args)

    @classmethod
    def get_argparse(
        cls: Type[THparams],
        f: Union[str, None, TextIO, pathlib.PurePath] = None,
        data: Optional[Dict[str, JSON]] = None,
        cli_args: Union[List[str], bool] = True,
    ) -> argparse.ArgumentParser:
        from yahp.create_object.create_object import get_argparse
        return get_argparse(cls, data=data, f=f, cli_args=cli_args)

    def to_yaml(self, **yaml_args: Any) -> str:
        """Serialize the object to a YAML string.

        Args:
            yaml_args: Extra arguments to pass into :func:`yaml.dump`.

        Returns:
            The object, as a yaml string.
        """
        return cast(str, yaml.dump(self.to_dict(), **yaml_args))

    def to_dict(self) -> Dict[str, JSON]:
        """
        Convert this object into a dict.

        Returns:
            The instance, as a JSON dictionary.
        """
        from yahp.serialization import get_key_for_instance_and_registry, serialize

        res: Dict[str, JSON] = {}
        for f in fields(self):
            if not f.init:
                continue
            attr = getattr(self, f.name)
            if attr is None:  # first, take care of the optionals
                res[f.name] = None
                continue

            # Is the field in the hparams registry?
            if self.hparams_registry is not None and f.name in self.hparams_registry:
                inverted_registry = {v: k for (k, v) in self.hparams_registry[f.name].items()}
                if isinstance(attr, list):
                    field_list: List[JSON] = []
                    for x in attr:
                        x_type = type(x)
                        key = get_key_for_instance_and_registry(x, self.hparams_registry[f.name])
                        if key is not None:
                            field_list.append({key: serialize(x)})
                        elif x_type in inverted_registry:
                            field_name = inverted_registry[x_type]
                            field_list.append({field_name: serialize(x)})
                        else:
                            # Cannot determine the key from the type
                            field_list.append(serialize(x))
                    res[f.name] = list_to_deduplicated_dict(field_list)
                else:
                    field_dict = {}
                    attr_type = type(attr)
                    key = get_key_for_instance_and_registry(attr, self.hparams_registry[f.name])
                    if key is not None:
                        field_dict[key] = serialize(attr)
                    elif attr_type in inverted_registry:
                        field_name = inverted_registry[type(attr)]
                        # Generic hparams. Make sure to index by the key in the hparams registry
                        field_dict[field_name] = serialize(attr)
                    else:
                        # Cannot determine the key from the type
                        field_dict = serialize(attr)
                    res[f.name] = field_dict

            else:
                # If it's not in the registry, then it must be specific
                is_list = isinstance(attr, list)
                if not is_list:
                    attr = [attr]
                ans = []
                for x in attr:
                    if x is None or isinstance(x, (str, float, bool, int, Enum, dict)):
                        ans.append(x.name if isinstance(x, Enum) else x)
                    else:
                        ans.append(serialize(x))
                if not is_list:
                    ans = ans[0]
                res[f.name] = ans

        return res

    def initialize_object(self, *args: Any, **kwargs: Any) -> Any:
        """
        Optional method to initialize an
        associated object from the :class:`Hparams`.

        Returns:
            The initialized object.
        """
        del args, kwargs
        raise NotImplementedError(
            textwrap.dedent("""Initializing object not supported for this Hparams.
            To enable, add initialize_object method."""))

    @classmethod
    def dump(
        cls,
        output: TextIO,
        add_docs: bool = True,
        typing_column: int = 45,
        interactive: bool = False,
    ) -> None:
        """Generate a YAML template for :class:`Hparams`
        and save the template to a file.

        Args:
            output (TextIO): File-like object to which to save the template.
            add_docs (bool, optional):
                Whether to add docs (as comments) to the YAML.
                Defaults to True.
            typing_column (int, optional):
                Column at which to add documentation. Defaults to 45.
                Ignored if If ``add_docs`` is False.
            interactive (bool, optional):
                Whether to interactively generate the template.
                Defaults to False.
        """
        from yahp.create_object.commented_map import CMOptions, to_commented_map

        cm = to_commented_map(
            constructor=cls,
            options=CMOptions(
                add_docs=add_docs,
                typing_column=typing_column,
                interactive=interactive,
            ),
            path=[],
        )
        y = YAML()
        y.dump(cm, output)

    @classmethod
    def dumps(
        cls,
        add_docs: bool = False,
        typing_column: int = 45,
        interactive: bool = False,
    ) -> str:
        """
        Generate a YAML template for :class:`Hparams`
        and returns the generated YAML as a string.

        Args:
            add_docs (bool, optional):
                Whether to add docs (as comments) to the YAML.
                Defaults to True.
            typing_column (int, optional):
                Column at which to add documentation. Defaults to 45.
                Ignored if If ``add_docs`` is False.
            interactive (bool, optional):
                Whether to interactively generate the template.
                Defaults to False.

        Returns:
            The generated YAML, as a string.

        """
        stream = StringIO()
        cls.dump(stream, add_docs=add_docs, typing_column=typing_column, interactive=interactive)
        return stream.getvalue()

    @classmethod
    def register_class(cls, field: str, register_class: Type[Hparams], class_key: str) -> None:
        """Dynamically add additional entries into the :attr:`Hparams.hparams_registry`.

        For abstract fields whose concrete classes are listed in the :attr:`Hparams.hparams_registry`,
        this function registers additional fields in the registry.

        Args:
            field (str): The field name
            register_class (Type[Hparams]): The additional class to register.
            class_key (str): The identifier to specify the class in CLI args and YAML.
        """
        class_fields = [x for x in fields(cls) if x.name == field]
        if len(class_fields) == 0:
            message = f'Unable to find field: {class_key}.{field} in: {cls.__name__}'
            logger.warning(message)
            raise ValueError(message)
        if cls.hparams_registry is None or field not in cls.hparams_registry:
            message = f'Unable to find field: {class_key}.{field} in: {cls.__name__} registry. \n'
            message += 'Is it a choose one or list Hparam?'
            logger.warning(message)
            raise ValueError(message)

        sub_registry = cls.hparams_registry[field]
        existing_keys = sub_registry.keys()
        if class_key in existing_keys:
            raise ValueError(
                textwrap.dedent(f"""Field {class_key}.{field} already registered in the {cls.__name__}
                "registry for class: {sub_registry[field]}. Make sure you register new classes with a unique name"""))

        logger.info(f'Successfully registered: {register_class.__name__} for key: {class_key} in {cls.__name__}')
        sub_registry[class_key] = register_class

    def validate(self):
        """Validate is deprecated"""
        warnings.warn(
            f'{type(self).__name__}.validate() is deprecated. Instead, perform any validation directly in initialize_object()',
            category=DeprecationWarning,
        )

    @classmethod
    def _build_json_schema(cls: Type[THparams], _cls_def: Dict[str, Any], allow_recursion: bool) -> None:
        """Recursive private helper for generating and returning a JSONSchema dictionary.

        Args:
            _cls_def (Optional[Dict[str, Any]]): Keeps a reference to previously built Hparmam
                classes and enums which can be used with references to make schemas more concise
                and readable.
            allow_recursion (bool): Whether to recursively parse subclasses.
        """
        res = {
            'type': 'object',
            'properties': {},
            'additionalProperties': False,
        }
        class_type_hints = get_type_hints(cls)
        for f in sorted(fields(cls), key=lambda f: f.name):
            if not f.init:
                continue

            # Required field
            if type_helpers.is_field_required(f):
                if 'required' not in res.keys():
                    res['required'] = []
                res['required'].append(f.name)

            hparams_type = type_helpers.HparamsType(class_type_hints[f.name])
            # Name is found in registry, set possible values as types in a union type
            if cls.hparams_registry and f.name in cls.hparams_registry and len(cls.hparams_registry[f.name].keys()) > 0:
                res['properties'][f.name] = get_registry_json_schema(hparams_type, cls.hparams_registry[f.name],
                                                                     _cls_def, allow_recursion)
            else:
                res['properties'][f.name] = get_type_json_schema(hparams_type, _cls_def, allow_recursion)
            res['properties'][f.name]['description'] = f.metadata['doc']

        # Add schema to _cls_def. Hparams classes are always inserted into defs and referenced to
        # in built schemas. If this function was called from `get_type_json_schema``, that function
        # will add a reference to this class. If this was called from the root Hparams class the
        # schema is being generated for, res will be pulled from _cls_defs
        _cls_def[cls.__qualname__] = res

    @classmethod
    def get_json_schema(cls: Type[THparams]) -> Dict[str, Any]:
        """Generates and returns a JSONSchema dictionary."""
        _cls_def = {}
        cls._build_json_schema(_cls_def=_cls_def, allow_recursion=True)
        res = _cls_def[cls.__qualname__]

        # Delete top level name. By default, all Hparams classes are added to _cls_def. However,
        # the top level Hparams class is not referenced anywhere (as it is the root), so we can
        # remove it from _cls_def.
        del _cls_def[cls.__qualname__]
        # Add definitions to top level of schema
        for key, value in _cls_def.items():
            if '$defs' not in res:
                res['$defs'] = {}
            res['$defs'][key] = value

        return res

    @classmethod
    def dump_jsonschema(cls: Type[THparams], f: Union[TextIO, str, pathlib.Path], **kwargs: Any):
        """Dump the JSONSchema to ``f``.

        Args:
            f (Union[str, None, TextIO, pathlib.PurePath], optional): Writes json to this file.
            kwargs: (Any): Keyword args to be passed to `json.dump`.
        """
        if isinstance(f, TextIO) or isinstance(f, TextIOWrapper):
            json.dump(cls.get_json_schema(), f, **kwargs)
        else:
            with open(f, 'w') as file:
                json.dump(cls.get_json_schema(), file, **kwargs)

    @classmethod
    def validate_yaml(cls: Type[THparams],
                      f: Union[str, None, TextIO, pathlib.PurePath] = None,
                      data: Optional[Dict[str, Any]] = None):
        """Validate yaml against JSON schema.

        Args:
            f (Union[str, None, TextIO, pathlib.PurePath], optional):
                If specified, loads values and validates from a YAML file. Can be either a
                filepath or file-like object.
                Cannot be specified with ``data``.
            data (Optional[str], optional):
                If specified, validates YAML specified by string :class:`Hparams`.
                Cannot be specified with ``f``.
        """
        if f and data:
            raise ValueError('File and data cannot both be specified.')
        elif f:
            if isinstance(f, TextIO) or isinstance(f, TextIOWrapper):
                jsonschema.validate(yaml.safe_load(f), cls.get_json_schema())
            else:
                with open(f) as file:
                    jsonschema.validate(yaml.safe_load(file), cls.get_json_schema())
        elif data:
            jsonschema.validate(data, cls.get_json_schema())
        else:
            raise ValueError('Neither file nor data were provided, so there is no YAML to validate.')

    def __str__(self) -> str:
        yaml_str = self.to_yaml().strip()
        yaml_str = textwrap.indent(yaml_str, '  ')
        output = f'{self.__class__.__name__}:\n{yaml_str}'
        return output
