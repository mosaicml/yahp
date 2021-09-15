from __future__ import annotations

import argparse
import collections.abc
import copy
import logging
import os
import pathlib
import textwrap
from abc import abstractmethod
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any, Callable, Dict, List, TextIO, Tuple, Type, Union, get_type_hints

import yaml

from yahp import type_helpers
from yahp.argparse import _add_args
from yahp.commented_map import _to_commented_map as commented_map
from yahp.create import _create_from_dict
from yahp.interactive import list_options, query_yes_no
from yahp.objects_helpers import HparamsException, StringDumpYAML
from yahp.types import JSON, THparams

# This is for ruamel.yaml not importing properly in conda
try:
    from ruamel_yaml import YAML  # type: ignore
except ImportError as e:
    from ruamel.yaml import YAML  # type: ignore

logger = logging.getLogger(__name__)


def required(doc: str, *args, template_default: Any = None, **kwargs):
    """A required field for a dataclass, including documentation."""

    if not isinstance(doc, str) or not doc:
        raise HparamsException(f'Invalid documentation: {doc}')

    default = None
    if 'default' in kwargs and 'default_factory' in kwargs:
        raise HparamsException('cannot specify both default and default_factory')
    elif 'default' in kwargs:
        default = kwargs['default']
    elif "default_factory" in kwargs:
        default = kwargs['default_factory']()
    return field(
        *args,
        metadata={
            'doc': doc,
            'default': default,
            'template_default': template_default,
        },
        **kwargs,
    )


def optional(doc: str, *args: Any, **kwargs: Any):
    """An optional field for a dataclass, including a default value and documentation."""

    if not isinstance(doc, str) or not doc:
        raise HparamsException(f'Invalid documentation: {doc}')

    if 'default' not in kwargs and 'default_factory' not in kwargs:
        raise HparamsException('Optional field must have default or default_factory defined')
    elif 'default' in kwargs and 'default_factory' in kwargs:
        raise HparamsException('cannot specify both default and default_factory')
    elif 'default' in kwargs:
        default = kwargs['default']
    else:
        default = kwargs['default_factory']()

    return field(
        *args,
        metadata={
            'doc': doc,
            'default': default,
            'template_default': default,
        },
        **kwargs,
    )


@dataclass
class Hparams:
    """
    A collection of hyperparameters with names, types, values, and documentation.

    Capable of converting back and forth between argparse flags and yaml.
    """

    # Can be a map from:
    #   field -> Hparam                           # for a single nested Hparam
    #   field -> Dict[str, Type[Hparam]]          # for multiple exclusive Hparam Options,
    # works for: choose one, list
    # note: hparams_registry cannot be typed otherwise subclasses cant instantiate
    hparams_registry = {}  # type: Dict[str, Union[Type["Hparams"], Dict[str, Type["Hparams"]]]]

    key_name = ""  # Used for helping determine what keyed name was used in creating the Hparams object

    helptext = ""

    @classmethod
    def _get_possible_items_for_registry_key(cls, registry_key) -> List[Tuple[str, Type["Hparams"]]]:
        if registry_key in cls.hparams_registry:
            vals = cls.hparams_registry[registry_key]
            if isinstance(vals, collections.abc.Mapping):
                return list(vals.items())
            elif type_helpers._is_hparams_type(vals):
                return [(registry_key, vals)]
            raise HparamsException("Hparams registry should only have singly nested Hparams or a dict of Hparams")

        else:
            return []

    @classmethod
    def _validate_keys(cls, data: Dict[str, Any], throw_error: bool = True, print_error: bool = True):
        keys_in_yaml = set(data.keys())
        keys_in_class = set([(f.name) for f in fields(cls)])
        required_keys_in_class = set([
            (f.name) for f in fields(cls) if type_helpers._get_required_default_from_field(f)[0]
        ])

        # Extra keys.
        if keys_in_yaml - keys_in_class:
            error_msg = f'Unexpected keys in {cls.__name__}: ' + ', '.join(list(keys_in_yaml - keys_in_class))
            if print_error:
                logger.error(error_msg)
            if throw_error:
                raise HparamsException(error_msg)

        # Missing keys.
        if required_keys_in_class - keys_in_yaml:
            err_msg = f'Required keys missing in {cls.__name__}: ' + ', '.join(
                list(required_keys_in_class - keys_in_yaml))
            if print_error:
                logger.error(err_msg)
            if throw_error:
                raise HparamsException(err_msg)

    @classmethod
    def _add_filename_argument(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-f",
            "--params_file",
            type=pathlib.Path,
            dest="filepath",
            help="Please set the path to the yaml that you would like to load as your Hparams",
        )

    @classmethod
    def interactive_template(cls):
        option_exit = "Exit"
        option_interactively_generate = "Generate Yaml Interactively"
        option_dump_generate = "Generate Full Yaml Dump"
        options = [
            option_interactively_generate,
            option_dump_generate,
            option_exit,
        ]

        pre_helptext = textwrap.dedent("""
        No Yaml found passed with -f to create Hparams
        Choose an option below to generate a yaml
        """)

        interactive_response = list_options(
            input_text=f"Please select an option",
            options=options,
            default_response=option_exit,
            pre_helptext=pre_helptext,
            multiple_ok=False,
            helptext=option_exit,
        )
        if interactive_response == option_exit:
            exit(0)
        elif interactive_response == option_interactively_generate or interactive_response == option_dump_generate:

            filename = None
            while not filename:
                default_filename = cls.__name__.lower().replace("hparams", "_hparams") + ".yaml"
                interactive = interactive_response == option_interactively_generate
                interactive_response = list_options(
                    input_text=f"Choose a file to dump to",
                    options=[default_filename],
                    default_response=default_filename,
                    pre_helptext="",
                    multiple_ok=False,
                    helptext=default_filename,
                )
                filename = interactive_response
                assert isinstance(filename, str)
                if os.path.exists(filename):
                    print(f"{filename} exists.")
                    if not query_yes_no(question=f"Overwrite {filename}?", default=True):
                        filename = None
                        continue

                with open(filename, "w") as f:
                    cls.dump(
                        output=f,
                        interactive=interactive,
                    )
                exit(0)

    @classmethod
    def create_from_dict(
        cls,
        data: Dict[str, JSON],
    ) -> Hparams:
        # Check against the schema.
        cls._validate_keys(data=data)

        return _create_from_dict(cls=cls, data=data)

    @classmethod
    def create(
        cls,
        filepath: str,
        argparse_overrides: bool = True,
    ) -> Hparams:  # type: ignore
        """
        Create an instance of this Hparams object from a yaml file with argparse overrides
        """
        with open(filepath, 'r') as f:
            data = yaml.full_load(f)

        if not argparse_overrides:
            return cls.create_from_dict(data=data)

        from yahp.argparse import _namespace_to_hparams_dict, _yaml_data_to_argparse_namespace
        yaml_argparse_namespace = _yaml_data_to_argparse_namespace(yaml_data=data)
        original_yaml_argparse_namespace = copy.deepcopy(yaml_argparse_namespace)
        parser = argparse.ArgumentParser()
        cls.add_args(parser=parser, defaults=yaml_argparse_namespace)

        args, unknown_args = parser.parse_known_args()
        if len(unknown_args):
            print(unknown_args)
            logger.warning(f"Unknown args: {unknown_args}")

        arg_items: List[Tuple[str, Any]] = list((vars(args)).items())

        argparse_data = _namespace_to_hparams_dict(
            cls=cls,
            namespace=arg_items,
        )

        parsed_argparse_namespace = _yaml_data_to_argparse_namespace(yaml_data=argparse_data)
        parsed_argparse_keys = set(parsed_argparse_namespace.keys())
        yaml_argparse_keys = set(original_yaml_argparse_namespace.keys())

        intersection_keys = parsed_argparse_keys.intersection(yaml_argparse_keys)
        first_override = True
        for key in intersection_keys:
            if parsed_argparse_namespace[key] != original_yaml_argparse_namespace[key]:
                if first_override:
                    print("\n" + "-" * 60 + "\nOverriding Yaml Keys\n" + "-" * 60 + "\n")
                    first_override = False
                print(
                    f"Overriding field: {key} from old value: {original_yaml_argparse_namespace[key]} with: {parsed_argparse_namespace[key]}"
                )
        added_keys = parsed_argparse_keys - yaml_argparse_keys

        if len(added_keys):
            print("\n" + "-" * 60 + "\nAdding Keys w/ defaults or Argparse\n" + "-" * 60 + "\n")
        for key in added_keys:
            print(f"Added: {key},  value: {parsed_argparse_namespace[key]}")

        removed_keys = yaml_argparse_keys - parsed_argparse_keys
        if len(removed_keys):
            print("\n" + "-" * 60 + "\nExtra Keys\n" + "-" * 60 + "\n")
        for key in removed_keys:
            print(f"Extra key: {key}, value: {original_yaml_argparse_namespace[key]}")
        if len(removed_keys):
            print("")
            raise Exception(f"Found extra keys in the yaml: {', '.join(removed_keys) }")

        return cls.create_from_dict(data=argparse_data)

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
            ftype = field_types[f.name]
            attr = getattr(self, f.name)
            if type_helpers._is_hparams_type(type_helpers._get_real_ftype(ftype)):
                if isinstance(attr, list):
                    res[f.name] = [{x.key_name: x.to_dict()} for x in attr]
                else:
                    # Directly nested vs choice
                    if f.name in self.hparams_registry and attr.key_name in self.hparams_registry[f.name]:
                        # Choice found
                        res[f.name] = {attr.key_name: attr.to_dict()}
                    else:
                        # Directly nested
                        res[f.name] = attr.to_dict()
            else:
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

    @abstractmethod
    def initialize_object(
        self,
        *args,
        **kwargs,
    ) -> object:
        """
        Optional method to intialize an associated object (e.g. for AdamHparams, torch.util.Adam)
        """
        raise NotImplementedError("Initializing object not supported for this Hparams. "
                                  "To enable, add initialize_object method.")

    @classmethod
    def add_args(
            cls,
            parser: argparse.ArgumentParser,
            prefix: List[str] = [],
            defaults: Dict[str, Any] = dict(),
    ) -> None:
        """
        Add the fields of the class as arguments to `parser`.

        Optionally, provide an instance of this class to serve as default arguments.
        Optionally, provide a prefix to apply to all flags that are added.
        Optionally, add all of these arguments to an argument group called `group_name` with
            description `group_description`.
        """
        _add_args(
            cls=cls,
            parser=parser,
            prefix=prefix,
            defaults=defaults,
        )

    @classmethod
    def dump(
        cls,
        output: TextIO,
        comment_helptext=False,
        typing_column=45,
        choice_option_column=35,
        interactive=False,
    ) -> None:
        cm = commented_map(
            cls=cls,
            comment_helptext=comment_helptext,
            typing_column=typing_column,
            choice_option_column=choice_option_column,
            interactive=interactive,
        )
        y = YAML()
        y.dump(cm, output)

    @classmethod
    def dumps(
        cls,
        comment_helptext=False,
        typing_column=45,
        choice_option_column=35,
        interactive=False,
    ) -> str:
        from yahp.commented_map import _to_commented_map as commented_map
        cm = commented_map(
            cls=cls,
            comment_helptext=comment_helptext,
            typing_column=typing_column,
            choice_option_column=choice_option_column,
            interactive=interactive,
        )
        s = StringDumpYAML()
        return s.dump(cm)  # type: ignore

    @classmethod
    def _to_json_primitive(cls, val: Union[Callable[[], THparams], THparams]) -> JSON:
        if callable(val):
            val = val()
        if isinstance(val, Enum):
            return val.value
        if val is None or isinstance(val, (str, float, int)):
            return val
        raise TypeError(f"Cannot convert value of type {type(val)} into a JSON primitive")

    def validate(self):
        field_types = get_type_hints(self.__class__)
        for field in fields(self):
            ftype = field_types[field.name]
            real_ftype = type_helpers._get_real_ftype(ftype)
            if type_helpers._is_json_dict(ftype):
                # TODO
                continue
            if type_helpers._is_primitive_optional_type(ftype):
                # TODO
                continue
            if type_helpers._is_list(ftype):
                # TODO
                continue
            if type_helpers._is_hparams_type(real_ftype):
                field_value = getattr(self, field.name)
                if isinstance(field_value, list):
                    for item in field_value:
                        item.validate()
                else:
                    # TODO: Look into how this can be done
                    if field_value:
                        field_value.validate()
                continue
            raise ValueError(f"{self.__class__.__name__}.{field.name} has invalid type: {ftype}")

    def __str__(self) -> str:
        yaml_str = self.to_yaml()
        yaml_str = textwrap.indent(yaml_str, "  ")
        output = f"{self.__class__.__name__}:\n{yaml_str}"
        return output
