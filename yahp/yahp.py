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
from typing import Any, Callable, Dict, List, Optional, Sequence, TextIO, Tuple, Type, Union, get_type_hints

import yaml

from yahp import type_helpers
from yahp.argparse import _add_args
from yahp.commented_map import _to_commented_map as commented_map
from yahp.create import _create_from_dict
from yahp.interactive import list_options, query_yes_no
from yahp.objects_helpers import StringDumpYAML, YAHPException
from yahp.types import JSON, THparams

# This is for ruamel.yaml not importing properly in conda
try:
    from ruamel_yaml import YAML  # type: ignore
except ImportError as e:
    from ruamel.yaml import YAML  # type: ignore

logger = logging.getLogger(__name__)


def required(doc: str, *args: Any, template_default: Any = None, **kwargs: Any):
    """A required field for a dataclass, including documentation."""

    if not isinstance(doc, str) or not doc:
        raise YAHPException(f'Invalid documentation: {doc}')

    default = None
    if 'default' in kwargs and 'default_factory' in kwargs:
        raise YAHPException('cannot specify both default and default_factory')
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
        raise YAHPException(f'Invalid documentation: {doc}')

    if 'default' not in kwargs and 'default_factory' not in kwargs:
        raise YAHPException('Optional field must have default or default_factory defined')
    elif 'default' in kwargs and 'default_factory' in kwargs:
        raise YAHPException('cannot specify both default and default_factory')
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
    helptext = ""

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
                raise YAHPException(error_msg)

        # Missing keys.
        if required_keys_in_class - keys_in_yaml:
            err_msg = f'Required keys missing in {cls.__name__}: ' + ', '.join(
                list(required_keys_in_class - keys_in_yaml))
            if print_error:
                logger.error(err_msg)
            if throw_error:
                raise YAHPException(err_msg)

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

        return _create_from_dict(cls=cls, data=data, prefix=[])

    @classmethod
    def create(
        cls,
        filepath: str,
        argparse_overrides: bool = True,
        args: Optional[Sequence[str]] = None,
    ) -> Hparams:  # type: ignore
        """
        Create an instance of this Hparams object from a yaml file with argparse overrides
        """
        with open(filepath, 'r') as f:
            data = yaml.full_load(f)

        if not argparse_overrides:
            return cls.create_from_dict(data=data)

        from yahp.argparse import _namespace_to_hparams_dict, _yaml_data_to_argparse_namespace
        yaml_argparse_namespace = _yaml_data_to_argparse_namespace(yaml_data=data, _prefix=[])
        original_yaml_argparse_namespace = copy.deepcopy(yaml_argparse_namespace)
        parser = argparse.ArgumentParser()
        cls.add_args(parser=parser, defaults=yaml_argparse_namespace, prefix=[])

        args, unknown_args = parser.parse_known_args(args=args)
        if len(unknown_args):
            print(unknown_args)
            logger.warning(f"Unknown args: {unknown_args}")

        arg_items: List[Tuple[str, Any]] = list((vars(args)).items())

        argparse_data = _namespace_to_hparams_dict(
            cls=cls,
            namespace=arg_items,
        )

        parsed_argparse_namespace = _yaml_data_to_argparse_namespace(yaml_data=argparse_data, _prefix=[])
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

        full_parsed_argparse_keys = set()
        for key in parsed_argparse_keys:
            full_parsed_argparse_keys.add(key)
            tokens = key.split('.')
            for i in range(len(tokens)):
                full_parsed_argparse_keys.add('.'.join(tokens[:-i - 1]))

        removed_keys = yaml_argparse_keys - full_parsed_argparse_keys
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
            if attr is None:  # first, take care of the optionals
                res[f.name] = None
                continue
            if type_helpers._is_hparams_type(type_helpers._get_real_ftype(ftype)):
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

    @abstractmethod
    def initialize_object(self) -> object:
        """
        Optional method to initialize an associated object (e.g. for AdamHparams, torch.util.Adam)
        """
        raise NotImplementedError("Initializing object not supported for this Hparams. "
                                  "To enable, add initialize_object method.")

    @classmethod
    def add_args(
        cls,
        parser: argparse.ArgumentParser,
        prefix: List[str],
        defaults: Dict[str, Any],
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
        comment_helptext: bool = False,
        typing_column: int = 45,
        choice_option_column: int = 35,
        interactive: bool = False,
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
        comment_helptext: bool = False,
        typing_column: int = 45,
        choice_option_column: int = 35,
        interactive: bool = False,
    ) -> str:
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
            ftype = field_types[f.name]
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
