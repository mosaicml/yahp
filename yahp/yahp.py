from __future__ import annotations

import logging
import pathlib
import textwrap
from abc import ABC
from dataclasses import _MISSING_TYPE, MISSING, dataclass, field, fields
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, TextIO, Type, Union, get_type_hints

import yaml

from yahp import type_helpers
from yahp.commented_map import CMOptions, to_commented_map
from yahp.create import create
from yahp.objects_helpers import StringDumpYAML, YAHPException

if TYPE_CHECKING:
    from yahp.types import JSON, SequenceStr, THparamsSubclass

# This is for ruamel.yaml not importing properly in conda
try:
    from ruamel_yaml import YAML  # type: ignore
except ImportError as e:
    from ruamel.yaml import YAML  # type: ignore

logger = logging.getLogger(__name__)


def required(doc: str, template_default: Any = MISSING):
    """A required field for a dataclass, including documentation."""
    return field(metadata={
        'doc': doc,
        'template_default': template_default,
    },)


def optional(doc: str, default: Any = MISSING, default_factory: Union[_MISSING_TYPE, Callable[[], Any]] = MISSING):
    """An optional field for a dataclass, including a default value and documentation."""
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
                      keys: SequenceStr,
                      *,
                      allow_missing_keys: bool = False,
                      allow_extra_keys: bool = False) -> None:
        keys_in_yaml = set(keys)
        keys_in_class = set([f.name for f in fields(cls) if f.init])
        required_keys_in_class = set(f.name for f in fields(cls) if f.init and type_helpers.is_field_required(f))

        extra_keys = list(keys_in_yaml - keys_in_class)
        missing_keys = list(required_keys_in_class - keys_in_yaml)

        if not allow_missing_keys and len(missing_keys) > 0:
            raise YAHPException(f'Required keys missing in {cls.__name__}', missing_keys)

        if not allow_extra_keys and len(extra_keys) > 0:
            raise YAHPException(f'Unexpected keys in {cls.__name__}: ', extra_keys)

    @classmethod
    def create(
        cls: Type[THparamsSubclass],
        f: Union[str, None, TextIO, pathlib.PurePath] = None,
        data: Optional[Dict[str, JSON]] = None,
        cli_args: Optional[List[str]] = None,
    ) -> THparamsSubclass:
        return create(cls, data=data, f=f, cli_args=cli_args)

    def to_yaml(self, **yaml_args: Any) -> str:
        """
        Serialize this object into a yaml string.
        """
        return yaml.dump(self.to_dict(), **yaml_args)  # type: ignore

    def to_dict(self) -> Dict[str, JSON]:
        """
        Convert this object into a dict.
        """

        res: Dict[str, JSON] = dict()
        field_types = get_type_hints(self.__class__)
        for f in fields(self):
            if f.init:
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
                        res[f.name] = [x.value for x in attr]
                    else:
                        res[f.name] = attr
                else:
                    if isinstance(attr, Enum):
                        res[f.name] = attr.value
                    else:
                        res[f.name] = attr
        return res

    def initialize_object(self, *args: Any, **kwargs: Any) -> Any:
        """
        Optional method to initialize an associated object (e.g. for AdamHparams, torch.util.Adam)
        """
        raise NotImplementedError("Initializing object not supported for this Hparams. "
                                  "To enable, add initialize_object method.")

    @classmethod
    def dump(
        cls,
        output: TextIO,
        add_docs: bool = True,
        typing_column: int = 45,
        choice_option_column: int = 35,
        interactive: bool = False,
    ) -> None:
        cm = to_commented_map(
            cls=cls,
            options=CMOptions(
                add_docs=add_docs,
                typing_column=typing_column,
                choice_option_column=choice_option_column,
                interactive=interactive,
            ),
        )
        y = YAML()
        y.dump(cm, output)

    @classmethod
    def dumps(
        cls,
        add_docs: bool = False,
        typing_column: int = 45,
        choice_option_column: int = 35,
        interactive: bool = False,
    ) -> str:
        cm = to_commented_map(
            cls=cls,
            options=CMOptions(
                add_docs=add_docs,
                typing_column=typing_column,
                choice_option_column=choice_option_column,
                interactive=interactive,
            ),
        )
        s = StringDumpYAML()
        return s.dump(cm)  # type: ignore

    @classmethod
    def register_class(cls, field: str, register_class: Type[Hparams], class_key: str) -> None:
        class_fields = [x for x in fields(cls) if x.name == field]
        if len(class_fields) == 0:
            message = f"Unable to find field: {field} in: {cls.__name__}"
            logger.warning(message)
            raise YAHPException(message)
        if field not in cls.hparams_registry:
            message = f"Unable to find field: {field} in: {cls.__name__} registry. \n"
            message += "Is it a choose one or list Hparam?"
            logger.warning(message)
            raise YAHPException(message)

        sub_registry = cls.hparams_registry[field]
        existing_keys = sub_registry.keys()
        if class_key in existing_keys:
            message = f"Field: {field} already registered in: {cls.__name__} registry for class: {sub_registry[field]}. \n"
            message += "Make sure you register new classes with a unique name"
            logger.warning(message)
            raise YAHPException(message)

        logger.info(f"Successfully registered: {register_class.__name__} for key: {class_key} in {cls.__name__}")
        sub_registry[class_key] = register_class

    def validate(self):
        field_types = get_type_hints(self.__class__)
        for f in fields(self):
            if f.init:
                continue
            ftype = type_helpers.HparamsType(field_types[f.name])
            if ftype.is_json_dict:
                # TODO
                continue
            if ftype.is_primitive:
                # TODO
                continue
            if ftype.is_enum:
                # TODO
                continue
            if ftype.is_list:
                # TODO
                continue
            if ftype.is_hparams_dataclass:
                field_value = getattr(self, f.name)
                if isinstance(field_value, list):
                    for item in field_value:
                        item.validate()
                else:
                    # TODO: Look into how this can be done
                    if field_value:
                        field_value.validate()
                continue
            raise ValueError(f"{self.__class__.__name__}.{f.name} has invalid type: {ftype}")

    def __str__(self) -> str:
        yaml_str = self.to_yaml()
        yaml_str = textwrap.indent(yaml_str, "  ")
        output = f"{self.__class__.__name__}:\n{yaml_str}"
        return output
