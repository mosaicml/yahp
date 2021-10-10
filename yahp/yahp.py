from __future__ import annotations

import argparse
import logging
import pathlib
import textwrap
import warnings
from abc import ABC
from dataclasses import MISSING, dataclass, field, fields
from enum import Enum
from io import StringIO
from typing import (TYPE_CHECKING, Any, Callable, Dict, List, Optional, TextIO, Type, TypeVar, Union, cast,
                    get_type_hints, overload)

import yaml

from yahp import type_helpers
from yahp.commented_map import CMOptions, to_commented_map
from yahp.create import create, get_argparse

if TYPE_CHECKING:
    from yahp.types import JSON, THparams

# This is for ruamel.yaml not importing properly in conda
try:
    from ruamel_yaml import YAML  # type: ignore
except ImportError as e:
    from ruamel.yaml import YAML  # type: ignore

logger = logging.getLogger(__name__)

TDefault = TypeVar("TDefault")


@overload
def required(doc: str) -> TDefault:
    pass


@overload
def required(doc: str, template_default: TDefault) -> TDefault:
    pass


def required(doc: str, template_default=MISSING):
    """
    A required field for a :class:`yahp.yahp.Hparams`.

    Args:
        doc (str): A description for the field. This description is included in :module:`argparse` help
            and the generated yaml template.
        template_default (Any, optional): Optional default to use when generating a template.

    Returns:
        A :class:`dataclasses.field`
    """
    return field(metadata={
        'doc': doc,
        'template_default': template_default,
    },)


@overload
def optional(doc: str, default: TDefault) -> TDefault:
    pass


@overload
def optional(doc: str, default_factory: Callable[[], TDefault]) -> TDefault:
    pass


def optional(doc: str, default=MISSING, default_factory=MISSING):
    """
    An optional field for a :class:`yahp.yahp.Hparams`. A default value can be optionally specified.
    If the default value is immutable, specify it via :param default:.
    Otherwise, specify a function that returns a new instance of the default value via :param default_factory:
    :param default: and :param default_factory: cannot both be specified.

    Args:
        doc (str): [desc
        default (Any, optional): Default value for the field. Cannot be specified with :param default_factory:.
        default_factory (Any, optional):
            A function that returns a default value for the field. Cannot be specified with :default:.

    Returns:
        A :class:`dataclasses.field`
    """
    return field(  # type: ignore
        metadata={
            'doc': doc,
        },
        default=default,
        default_factory=default_factory,
    )


@dataclass
class Hparams(ABC):
    """
    A collection of hyperparameters with names, types, values, and documentation.

    Capable of converting back and forth between argparse flags and yaml.
    """

    # hparams_registry is used to store generic arguments and the types that they could be.
    # For example, suppose Animal is an abstract type, and there is the field.
    # class Petstore(hp.Hparams):
    #     animal: Animal = hp.optional(...)
    #
    # Suppose there are two types of animals -- `Cat` and `Dog`. Then, the hparams registry should be:
    # hparams_registry = { "animal": {"cat": Cat, "dog": Dog } }
    # Then, the following yaml:
    #
    # animal:
    #   cat: {}
    #
    # Would result in the hparams being parsed as type(petstore.animal) == Cat
    #
    # Now consider when multiple values are allowed -- e.g.
    #
    # class Petstore(hp.Hparams):
    #     animals: List[Animal] = hp.optional(...)
    #
    # With the same hparams_registry as before, the following yaml:
    #
    # animal:
    #   - cat: {}
    #   - dog: {}
    #
    # would result in the hparams being parsed as:
    # type(petstore.animals) == list
    # type(petstore.animals[0]) == Cat
    # type(petstore.animals[1]) == Dog
    #
    # note: hparams_registry cannot be typed the normal way -- dataclass reads the type annotations
    # and would treat it like an instance variable. Instead, using the python2-style annotations
    hparams_registry = {}  # type: Dict[str, Dict[str, Type["Hparams"]]]

    @classmethod
    def validate_keys(cls,
                      keys: List[str],
                      *,
                      allow_missing_keys: bool = False,
                      allow_extra_keys: bool = False) -> None:
        """
        Validates that :param keys: matches the fields of the :class:`Hparams`.

        Args:
            keys (List[str]): Keys to validate.
            allow_missing_keys (bool, optional): Whether to ignore fields that do not have default values
                and are also not specified in :param keys:. Defaults to False.
            allow_extra_keys (bool, optional): Whether to allow extra members of :param keys:
                that are not present in the :class:`Hparams`. Defaults to False.

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
                If specified, load values from a YAML file. Can be either a filepath or file-like object.
                Cannot be specified with :param data:.
            data (Optional[Dict[str, JSON]], optional): If specified, uses this dictionary for instantiating
                the :class:`Hparams`. Cannot be specified with :param f:.
            cli_args (Union[List[str], bool], optional): CLI argument overrides.
                If `true` (the default), load CLI arguments from `sys.argv`.
                If `false`, then do not use any CLI arguments.

        Returns:
            THparams: An instance of :class:`Hparams`.
        """
        return create(cls, data=data, f=f, cli_args=cli_args)

    @classmethod
    def get_argparse(
        cls: Type[THparams],
        f: Union[str, None, TextIO, pathlib.PurePath] = None,
        data: Optional[Dict[str, JSON]] = None,
        cli_args: Union[List[str], bool] = True,
    ) -> argparse.ArgumentParser:
        return get_argparse(cls, data=data, f=f, cli_args=cli_args)

    def to_yaml(self, **yaml_args: Any) -> str:
        """Serialize the object to a YAML string.

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

        res: Dict[str, JSON] = dict()
        field_types = get_type_hints(self.__class__)
        for f in fields(self):
            if not f.init:
                continue
            ftype = type_helpers.HparamsType(field_types[f.name])
            attr = getattr(self, f.name)
            if attr is None:  # first, take care of the optionals
                res[f.name] = None
                continue
            if ftype.is_hparams_dataclass:
                # Could be: List[Generic Hparams], Generic Hparams,
                # List[Specific Hparams], or Specific Hparams
                # If it's in the registry, it's generic. Otherwise, it's specific
                if f.name in self.hparams_registry:
                    inverted_registry = {v: k for (k, v) in self.hparams_registry[f.name].items()}
                    if isinstance(attr, list):
                        field_list: List[JSON] = []
                        for x in attr:
                            assert isinstance(x, Hparams)
                            field_name = inverted_registry[type(x)]
                            field_list.append({field_name: x.to_dict()})
                        res[f.name] = field_list
                    else:
                        field_dict: Dict[str, JSON] = {}
                        field_name = inverted_registry[type(attr)]
                        # Generic hparams. Make sure to index by the key in the hparams registry
                        field_dict[field_name] = attr.to_dict()
                        res[f.name] = field_dict
                else:
                    # Specific -- either a list or not
                    if isinstance(attr, list):
                        res[f.name] = [x.to_dict() for x in attr]
                    else:
                        assert isinstance(attr, Hparams)
                        res[f.name] = attr.to_dict()
            else:
                # Not a hparams type
                if isinstance(attr, list):
                    if len(attr) and isinstance(attr[0], Enum):
                        res[f.name] = [x.name for x in attr]
                    else:
                        res[f.name] = attr
                else:
                    if isinstance(attr, Enum):
                        res[f.name] = attr.name
                    else:
                        res[f.name] = attr
        return res

    def initialize_object(self, *args: Any, **kwargs: Any) -> Any:
        """
        Optional method to initialize an associated object from the :class:`Hparams`.
        This method must be implemented for each :class:`Hparams`.

        Returns:
            The initialized object.
        """
        del args, kwargs
        raise NotImplementedError("Initializing object not supported for this Hparams. "
                                  "To enable, add initialize_object method.")

    @classmethod
    def dump(
        cls,
        output: TextIO,
        add_docs: bool = True,
        typing_column: int = 45,
        interactive: bool = False,
    ) -> None:
        """Generate a YAML template for :class:`Hparams` and save the template to a file.

        Args:
            output (TextIO): Output file-like object.
            add_docs (bool, optional): Whether to add docs (as comments) to the YAML. Defaults to True.
            typing_column (int, optional): Column at which to add documentation. Defaults to 45.
            interactive (bool, optional): [description]. Whether to interactively generate the template. Defaults to False.
        """
        cm = to_commented_map(
            cls=cls,
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
        """Generate a YAML template for :class:`Hparams`, and returns the generated YAML as a string.

        Args:
            add_docs (bool, optional): Whether to add docs (as comments) to the YAML. Defaults to True.
            typing_column (int, optional): Column at which to add documentation. Defaults to 45.
            interactive (bool, optional): [description]. Whether to interactively generate the template.
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
            message = f"Unable to find field: {class_key}.{field} in: {cls.__name__}"
            logger.warning(message)
            raise ValueError(message)
        if field not in cls.hparams_registry:
            message = f"Unable to find field: {class_key}.{field} in: {cls.__name__} registry. \n"
            message += "Is it a choose one or list Hparam?"
            logger.warning(message)
            raise ValueError(message)

        sub_registry = cls.hparams_registry[field]
        existing_keys = sub_registry.keys()
        if class_key in existing_keys:
            message = f"Field {class_key}.{field} already registered in: {cls.__name__} registry for class: {sub_registry[field]}. \n"
            message += "Make sure you register new classes with a unique name"
            logger.warning(message)
            raise ValueError(message)

        logger.info(f"Successfully registered: {register_class.__name__} for key: {class_key} in {cls.__name__}")
        sub_registry[class_key] = register_class

    def validate(self):
        """Validate that the hparams are of the correct types.
        Recurses through sub-hparams.

        Raises:
            TypeError: Raises a :class:`TypeError` if any fields are an incorrect type.
        """
        field_types = get_type_hints(self.__class__)
        for f in fields(self):
            if not f.init:
                continue
            fname = f.name
            ftype = type_helpers.HparamsType(field_types[f.name])
            value = getattr(self, f.name)
            if ftype.is_optional:
                if value is None:
                    continue
            if ftype.is_json_dict:
                if not isinstance(value, dict):
                    raise TypeError(f"{fname} must be a {ftype}; instead it is of type {type(value)}")
                continue
            if not ftype.is_hparams_dataclass:
                if ftype.is_list:
                    if not isinstance(value, list):
                        raise TypeError(f"{fname} must be a {ftype}; instead it is of type {type(value)}")
                else:
                    value = [value]
                for x in value:
                    if ftype.is_enum:
                        if not isinstance(x, ftype.type):
                            raise TypeError(f"{fname} must be a {ftype}; instead it is of type {type(x)}")
                        continue
                    if ftype.is_primitive:
                        is_allowed = False
                        for allowed_type in ftype.types:
                            if isinstance(x, allowed_type):
                                is_allowed = True
                                break
                        if not is_allowed:
                            raise TypeError(f"{fname} must be a {ftype}; instead it is of type {type(x)}")
                        continue
                    warnings.warn(f"{ftype} cannot be validated. This is a bug in YAHP. Please submit a bug report.")
                continue
            # is hparams
            if ftype.is_list:
                if not isinstance(value, list):
                    raise TypeError(f"{fname} must be a {ftype}; instead it is of type {type(value)}")
                continue
            value = [value]
            for x in value:
                if not isinstance(x, ftype.type):
                    raise TypeError(f"{fname} must be a {ftype}; instead it is of type {type(value)}")
                assert isinstance(x, Hparams)
                x.validate()

    def __str__(self) -> str:
        yaml_str = self.to_yaml().strip()
        yaml_str = textwrap.indent(yaml_str, "  ")
        output = f"{self.__class__.__name__}:\n{yaml_str}"
        return output
