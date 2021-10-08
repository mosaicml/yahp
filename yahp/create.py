# pyright: strict
# pyright: reportPrivateUsage=none
# pyright: reportUnnecessaryIsInstance=none
# pyright: reportUnnecessaryComparison=none

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys
import warnings
from dataclasses import _MISSING_TYPE, MISSING, InitVar, asdict, dataclass, field, fields
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Set, TextIO, Tuple, Type, Union, get_type_hints

import yaml

import yahp as hp
from yahp.inheritance import load_yaml_with_inheritance
from yahp.type_helpers import HparamsType, get_default_value, is_field_required, is_none_like, safe_issubclass, to_bool
from yahp.utils import extract_only_item_from_dict

if TYPE_CHECKING:
    from yahp.types import JSON, SequenceStr, THparams, THparamsSubclass


def _emit_should_be_list_warning(arg_name: str):
    warnings.warn(f"MalformedYAMLWarning: {arg_name} should be a list, not a singular element.")


logger = logging.getLogger(__name__)


class _ArgparseNameRegistry:

    def __init__(self) -> None:
        self._names: Set[str] = set()

    def add(self, *names: str) -> None:
        for name in names:
            if name in self._names:
                raise ValueError(f"{name} is already in the registry")
            self._names.add(name)

    def safe_add(self, name: str) -> str:
        if name not in self._names:
            self._names.add(name)
            return name
        i = 1
        candidate = f"name{i}"
        while name + str(i) in self._names:
            i += 1
        self._names.add(candidate)
        return candidate

    def __contains__(self, name: str) -> bool:
        return name in self._names


def _get_hparams_file_from_cli(*, cli_args: List[str], argparse_name_registry: _ArgparseNameRegistry,
                               argument_parsers: List[argparse.ArgumentParser]) -> Optional[str]:
    parser = argparse.ArgumentParser(add_help=False)
    argument_parsers.append(parser)
    argparse_name_registry.add("f", "file")
    parser.add_argument("-f", "--file", type=str, default=None, required=False, help="YAML file containing hparams")
    parsed_args, cli_args[:] = parser.parse_known_args(cli_args)
    return parsed_args.file


def _get_cm_options_from_cli(*, cli_args: List[str], argparse_name_registry: _ArgparseNameRegistry,
                             argument_parsers: List[argparse.ArgumentParser]) -> Optional[Tuple[str, bool, bool]]:
    parser = argparse.ArgumentParser(add_help=False)
    argument_parsers.append(parser)

    argparse_name_registry.add("s", "save_template", "i", "interactive", "d", "no_docs")

    parser.add_argument(
        "-s",
        "--save_template",
        type=str,
        const="stdout",
        nargs="?",
        default=None,
        required=False,
        metavar="stdout",
        help="If present, generate a hparams template and dump the template to the specified file (defaults to stdout)."
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        default=False,
        help=
        "Whether to generate the template interactively. Otherwise, will dump everything. Only applicible if --save_template is present."
    )

    parser.add_argument(
        "-d",
        "--no_docs",
        action="store_true",
        default=False,
        help="Whether to skip adding documentation to the generated YAML. Only applicible if --save_template is present."
    )
    parsed_args, cli_args[:] = parser.parse_known_args(cli_args)
    if parsed_args.save_template is None:
        return  # don't generate a template

    return parsed_args.save_template, parsed_args.interactive, not parsed_args.no_docs


class _MissingRequiredFieldException(ValueError):
    pass


@dataclass
class ParserArgument:
    # if arg_type is None, then it should not have any entry in the argparse.
    # useful to represent its children
    argparse_name_registry: InitVar[_ArgparseNameRegistry]
    full_name: str
    helptext: str
    nargs: Optional[str]
    child_hparams: Union[Dict[str, Type[hp.Hparams]], None, Type[hp.Hparams]] = None
    choices: Optional[SequenceStr] = None
    short_name: Optional[str] = field(init=False)

    def __post_init__(self, argparse_name_registry: _ArgparseNameRegistry) -> None:
        # register the full name in argparse_name_registry
        # also attempt to register a short name in argparse_name_registry
        self.full_name = argparse_name_registry.safe_add(self.full_name)

        # attempt to get a short name
        for shortness_index in range(len(self.full_name.split(".")) - 1):
            # TODO this appears to be broken
            # Counts leaves for conflicts
            short_name = self.get_possible_short_name(index=shortness_index)
            if short_name not in argparse_name_registry:
                argparse_name_registry.add(short_name)
                self.short_name = short_name
                break
        self.short_name = None

    def get_possible_short_name(self, index: int):
        items = self.full_name.split(".")[-(index + 1):]
        return ".".join(items)

    def __str__(self) -> str:
        return yaml.dump(asdict(self))  # type: ignore

    def add_to_argparse(self, container: argparse._ActionsContainer) -> None:
        names = [f"--{self.full_name}"]
        if self.short_name is not None and self.short_name != self.full_name:
            names.insert(0, f"--{self.short_name}")
        # not using argparse choices as they are too strict (e.g. case sensitive)
        metavar = self.full_name.split(".")[-1].upper()
        if self.choices is not None:
            metavar = f"{{{','.join(self.choices)}}}"
        container.add_argument(
            *names,
            nargs=self.nargs,  # type: ignore
            # using a sentinel to distinguish between a missing value and a default value that could have been overridden in yaml
            default=MISSING,
            type=cli_to_json,
            const=True if self.nargs == "?" else None,
            help=self.helptext,
            metavar=metavar,
        )


def cli_to_json(val: Union[str, _MISSING_TYPE]) -> Union[str, bool, float, None, _MISSING_TYPE]:
    if val == MISSING:
        return val
    assert not isinstance(val, _MISSING_TYPE)
    if isinstance(val, str) and val.strip().lower() in ("", "none"):
        return None
    for t in (bool, float, int):
        # bool, float, and int are mutually exclusive
        try:
            return to_bool(val) if t is bool else t(val)
        except (TypeError, ValueError):
            pass
    return val


def _retrieve_args(
    cls: Type[hp.Hparams],
    prefix: SequenceStr,
    argparse_name_registry: _ArgparseNameRegistry,
) -> Sequence[ParserArgument]:
    """get_argparse_group returns a argparse ArgumentGroup representing the arguments for a hp.Hparams
    It does not recurse.

    Args:
        cls (Type[hp.Hparams]): The Hparams class
        prefix (List[str]): The path containing the keys from the top-level :class:`hp.Hparams` to :arg:`cls`
        parent_group (argparse._ActionsContainer): The :class:`argparse._ActionsContainer` to add a :class:`argparse._ArgumentGroup` for the :arg:`cls`
    Returns:
        A sequence of :class:`ParserArgument` for this class. This is not computed recursively, to allow for lazily loading cli arguments.
    """
    type_hints = get_type_hints(cls)
    ans: List[ParserArgument] = []
    for f in fields(cls):
        if not f.init:
            continue
        ftype = HparamsType(type_hints[f.name])
        full_prefix = ".".join(prefix)
        if len(prefix):
            full_name = f'{full_prefix}.{f.name}'
        else:
            full_name = f'{f.name}'
        type_name = str(ftype)
        helptext = f"<{type_name}> {f.metadata['doc']}"

        required = is_field_required(f)
        default = get_default_value(f)
        if required:
            helptext = f'(required): {helptext}'
        if default != MISSING:
            if default is None or safe_issubclass(default, (int, float, str, Enum)):
                helptext = f"{helptext} (Default: {default})."
            elif safe_issubclass(default, hp.Hparams):
                helptext = f"{helptext} (Default: {type(default).__name__})."

        # Assumes that if a field default is supposed to be None it will not appear in the namespace
        if safe_issubclass(type(default), hp.Hparams):
            # if the default is hparams, set the argparse default to the hparams registry key
            # for this hparams object
            if f.name in cls.hparams_registry:
                inverted_field_registry = {v: k for (k, v) in cls.hparams_registry[f.name].items()}
                default = inverted_field_registry[type(default)]

        if not ftype.is_hparams_dataclass:
            nargs = None
            if ftype.is_list:
                nargs = "*"
            elif ftype.is_boolean:
                nargs = "?"
            choices = None
            if ftype.is_enum:
                choices = [x.name.lower() for x in ftype.type]
            if ftype.is_boolean and len(ftype.types) == 1:
                choices = ["true", "false"]
            if choices is not None and ftype.is_optional:
                choices.append("none")

            ans.append(
                ParserArgument(
                    argparse_name_registry=argparse_name_registry,
                    full_name=full_name,
                    nargs=nargs,
                    choices=choices,
                    helptext=helptext,
                ))
        else:
            # Split into choose one
            if f.name not in cls.hparams_registry:
                # Defaults to direct nesting if missing from hparams_registry
                if ftype.is_list:
                    # if it's a list of singletons, then print a warning and skip it
                    # Will use the default or yaml-provided value
                    logger.info("%s cannot be set via CLI arguments", full_name)
                elif ftype.is_optional:
                    # add a field to argparse that can be set to none to override the yaml (or default)
                    ans.append(
                        ParserArgument(
                            argparse_name_registry=argparse_name_registry,
                            full_name=full_name,
                            nargs=nargs,
                            helptext=helptext,
                        ))
            else:
                # Found in registry
                registry_entry = cls.hparams_registry[f.name]
                choices = sorted(list(registry_entry.keys()))
                nargs = None
                if ftype.is_list:
                    nargs = "+" if required else "*"
                    required = False
                ans.append(
                    ParserArgument(
                        argparse_name_registry=argparse_name_registry,
                        full_name=full_name,
                        nargs=nargs,
                        choices=choices,
                        helptext=helptext,
                        child_hparams=registry_entry,
                    ))
    return ans


def _load(*, cls: Type[THparamsSubclass], data: Dict[str, JSON], cli_args: Optional[List[str]], prefix: SequenceStr,
          argparse_name_registry: _ArgparseNameRegistry, argparsers: List[argparse.ArgumentParser]) -> THparamsSubclass:
    if cli_args is None:
        parsed_arg_dict = {}
    else:
        args = _retrieve_args(cls, prefix, argparse_name_registry)
        parser = argparse.ArgumentParser(add_help=False)
        group = parser
        if len(prefix):
            group = parser.add_argument_group(title=".".join(prefix), description=cls.__name__)
        for arg in args:
            arg.add_to_argparse(group)
        parsed_arg_namespace, cli_args[:] = parser.parse_known_args(cli_args)
        parsed_arg_dict = vars(parsed_arg_namespace)
        argparsers.append(parser)
    kwargs: Dict[str, THparams] = {}
    missing_required_fields: List[str] = [
    ]  # keep track of missing required fields so we can build a nice error message
    cls.validate_keys(list(data.keys()), allow_missing_keys=True)
    for f in fields(cls):
        if not f.init:
            continue
        prefix_with_fname = list(prefix) + [f.name]
        try:
            ftype = HparamsType(f.type)
            full_name = ".".join(prefix_with_fname)
            argparse_or_yaml_value: Union[_MISSING_TYPE, JSON] = MISSING
            if full_name in parsed_arg_dict and parsed_arg_dict[full_name] != MISSING:
                argparse_or_yaml_value = parsed_arg_dict.pop(full_name)
            elif f.name in data:
                argparse_or_yaml_value = data[f.name]
            elif full_name.upper() in os.environ:
                argparse_or_yaml_value = os.environ[full_name.upper()]

            if not ftype.is_hparams_dataclass:
                if argparse_or_yaml_value != MISSING:
                    kwargs[f.name] = ftype.convert(argparse_or_yaml_value, full_name)
                # defaults will be set by the hparams constructor
            else:
                if f.name not in cls.hparams_registry:
                    # concrete, singleton hparams
                    # list of concrete hparams
                    # potentially none
                    if not ftype.is_list:
                        # concrete, singleton hparams
                        # potentially none
                        if ftype.is_optional and is_none_like(argparse_or_yaml_value, allow_list=ftype.is_list):
                            # none
                            kwargs[f.name] = None
                        else:
                            # concrete, singleton hparams
                            sub_yaml = data.get(f.name)
                            if sub_yaml is None:
                                sub_yaml = {}
                            if not isinstance(sub_yaml, dict):
                                raise ValueError(f"{full_name} must be a dict in the yaml")
                            kwargs[f.name] = _load(cls=ftype.type,
                                                   data=sub_yaml,
                                                   prefix=prefix_with_fname,
                                                   cli_args=cli_args,
                                                   argparse_name_registry=argparse_name_registry,
                                                   argparsers=argparsers)
                    else:
                        # list of concrete hparams
                        # potentially none
                        # concrete lists not added to argparse, so just load the yaml
                        if ftype.is_optional and is_none_like(argparse_or_yaml_value, allow_list=ftype.is_list):
                            # none
                            kwargs[f.name] = None
                        else:
                            # list of concrete hparams
                            # concrete lists not added to argparse, so just load the yaml
                            sub_yaml = data.get(f.name)
                            if sub_yaml is None:
                                sub_yaml = []
                            if isinstance(sub_yaml, dict):
                                _emit_should_be_list_warning(full_name)
                                sub_yaml = [sub_yaml]
                            if not isinstance(sub_yaml, list):
                                raise TypeError(f"{full_name} must be a list in the yaml")
                            hparams_list: List[hp.Hparams] = []
                            for (i, sub_yaml_item) in enumerate(sub_yaml):
                                if sub_yaml_item is None:
                                    sub_yaml_item = {}
                                if not isinstance(sub_yaml_item, dict):
                                    raise TypeError(f"{full_name} must be a dict in the yaml")
                                sub_hparams = _load(
                                    cls=ftype.type,
                                    prefix=prefix_with_fname + [str(i)],
                                    data=sub_yaml_item,
                                    cli_args=None,
                                    argparse_name_registry=argparse_name_registry,
                                    argparsers=argparsers,
                                )
                                hparams_list.append(sub_hparams)
                            kwargs[f.name] = hparams_list
                else:
                    # abstract, singleton hparams
                    # list of abstract hparams
                    # potentially none
                    if not ftype.is_list:
                        # abstract, singleton hparams
                        # potentially none
                        if ftype.is_optional and is_none_like(argparse_or_yaml_value, allow_list=ftype.is_list):
                            # none
                            kwargs[f.name] = None
                        else:
                            # abstract, singleton hparams
                            # look up type in the registry
                            # should only have one key in the dict
                            # argparse_or_yaml_value is a str if argparse, or a dict if yaml
                            if argparse_or_yaml_value == MISSING:
                                # use the hparams default
                                continue
                            if argparse_or_yaml_value is None:
                                raise ValueError(f"Field {full_name} is required and cannot be None.")
                            if isinstance(argparse_or_yaml_value, str):
                                key = argparse_or_yaml_value
                            else:
                                if not isinstance(argparse_or_yaml_value, dict):
                                    raise ValueError(
                                        f"Field {full_name} must be a dict with just one key if specified in the yaml")
                                try:
                                    key, _ = extract_only_item_from_dict(argparse_or_yaml_value)
                                except ValueError as e:
                                    raise ValueError(f"Field {full_name} " + e.args[0])
                            yaml_val = data.get(f.name)
                            if yaml_val is None:
                                yaml_val = {}
                            if not isinstance(yaml_val, dict):
                                raise ValueError(
                                    f"Field {'.'.join(prefix_with_fname)} must be a dict if specified in the yaml")
                            yaml_val = yaml_val.get(key)
                            if yaml_val is None:
                                yaml_val = {}
                            if not isinstance(yaml_val, dict):
                                raise ValueError(
                                    f"Field {'.'.join(prefix_with_fname + [key])} must be a dict if specified in the yaml"
                                )
                            kwargs[f.name] = _load(cls=cls.hparams_registry[f.name][key],
                                                   prefix=prefix_with_fname + [key],
                                                   data=yaml_val,
                                                   cli_args=cli_args,
                                                   argparse_name_registry=argparse_name_registry,
                                                   argparsers=argparsers)
                    else:
                        # list of abstract hparams
                        # potentially none
                        if ftype.is_optional and is_none_like(argparse_or_yaml_value, allow_list=ftype.is_list):
                            # none
                            kwargs[f.name] = None
                        else:
                            # list of abstract hparams
                            # argparse_or_yaml_value is a List[str] if argparse, or a List[Dict[str, Hparams]] if yaml
                            if argparse_or_yaml_value == MISSING:
                                # use the hparams default
                                continue

                            # First get the keys
                            # Argparse has precidence. If there are keys defined in argparse, use only those
                            # These keys will determine what is loaded
                            if argparse_or_yaml_value is None:
                                raise ValueError(f"Field {full_name} is required and cannot be None.")
                            if isinstance(argparse_or_yaml_value, dict):
                                _emit_should_be_list_warning(full_name)
                                argparse_or_yaml_value = [argparse_or_yaml_value]
                            if not isinstance(argparse_or_yaml_value, list):
                                raise ValueError(f"Field {full_name} should be a list")
                            keys: List[str] = []
                            for item in argparse_or_yaml_value:
                                if isinstance(item, str):
                                    keys.append(item)
                                else:
                                    if not isinstance(item, dict):
                                        raise ValueError(f"Field {full_name} should be a list of dicts in the yaml")
                                    key, _ = extract_only_item_from_dict(item)
                                    keys.append(key)
                                key = argparse_or_yaml_value

                            # Now, load the values for these keys
                            yaml_val = data.get(f.name)
                            if yaml_val is None:
                                yaml_val = []
                            if isinstance(yaml_val, dict):
                                # already emitted the warning, no need to do it again
                                yaml_val = [yaml_val]
                            if not isinstance(yaml_val, list):
                                raise ValueError(
                                    f"Field {'.'.join(prefix_with_fname)} must be a list if specified in the yaml")
                            sub_hparams_list: List[hp.Hparams] = []

                            # Convert the yaml list to a dict
                            yaml_dict: Dict[str, Dict[str, JSON]] = {}
                            for i, yaml_val_entry in enumerate(yaml_val):
                                if not isinstance(yaml_val_entry, dict):
                                    raise ValueError(
                                        f"Field {'.'.join(list(prefix_with_fname) + [str(i)])} must be a dict if specified in the yaml"
                                    )
                                k, v = extract_only_item_from_dict(yaml_val_entry)
                                if not isinstance(v, dict):
                                    raise ValueError(
                                        f"Field {'.'.join(list(prefix_with_fname) + [k])} must be a dict if specified in the yaml"
                                    )
                                yaml_dict[k] = v

                            for key in keys:
                                # Use the order of keys
                                key_yaml = yaml_dict.get(key)
                                if key_yaml is None:
                                    key_yaml = {}
                                if not isinstance(key_yaml, dict):
                                    raise ValueError(
                                        f"Field {'.'.join(prefix_with_fname + [key])} must be a dict if specified in the yaml"
                                    )
                                sub_hparams = _load(cls=cls.hparams_registry[f.name][key],
                                                    prefix=prefix_with_fname + [key],
                                                    data=key_yaml,
                                                    cli_args=cli_args,
                                                    argparse_name_registry=argparse_name_registry,
                                                    argparsers=argparsers)
                                sub_hparams_list.append(sub_hparams)
                            kwargs[f.name] = sub_hparams_list
        except _MissingRequiredFieldException as e:
            missing_required_fields.extend(e.args)
            # continue processing the other fields and gather everything together

    for f in fields(cls):
        if not f.init:
            continue
        prefix_with_fname = ".".join(list(prefix) + [f.name])
        if f.name not in kwargs:
            if f.default == MISSING and f.default_factory == MISSING:
                missing_required_fields.append(prefix_with_fname)
            # else:
            #     warnings.warn(f"DefaultValueWarning: Using default value for {prefix_with_fname}. "
            #                   "Using default values is not recommended as they may change between versions.")
    if len(missing_required_fields) > 0:
        # if there are any missing fields from this class, or optional but partially-filled-in subclasses,
        # then propegate back the missing fields
        raise _MissingRequiredFieldException(*missing_required_fields)
    return cls(**kwargs)


def _add_help(argparsers: Sequence[argparse.ArgumentParser]) -> None:
    help_argparser = argparse.ArgumentParser(parents=argparsers)
    help_argparser.parse_known_args()  # Will print help and exit if the "--help" flag is present


def create(cls: Type[THparamsSubclass],
           data: Optional[Dict[str, JSON]] = None,
           f: Union[str, TextIO, pathlib.PurePath, None] = None,
           cli_args: Optional[SequenceStr] = None) -> THparamsSubclass:
    remaining_cli_args = list(sys.argv if cli_args is None else cli_args)

    argparse_name_registry = _ArgparseNameRegistry()
    argparsers: List[argparse.ArgumentParser] = []

    cm_options = _get_cm_options_from_cli(cli_args=remaining_cli_args,
                                          argparse_name_registry=argparse_name_registry,
                                          argument_parsers=argparsers)
    if cm_options is not None:
        output_file, interactive, add_docs = cm_options
        print(f"Generating a template for {cls.__name__}")
        if output_file == "stdout":
            cls.dump(add_docs=add_docs, interactive=interactive, output=sys.stdout)
        elif output_file == "stderr":
            cls.dump(add_docs=add_docs, interactive=interactive, output=sys.stderr)
        else:
            with open(output_file, "x") as f:
                cls.dump(add_docs=add_docs, interactive=interactive, output=f)
        # exit so we don't attempt to parse and instantiate if generate template is passed
        print()
        print("Finished")
        sys.exit(0)

    cli_f = _get_hparams_file_from_cli(cli_args=remaining_cli_args,
                                       argparse_name_registry=argparse_name_registry,
                                       argument_parsers=argparsers)
    if cli_f is not None:
        if f is not None:
            raise ValueError("File cannot be specifed via both function arguments and the CLI")
        f = cli_f

    if f is not None:
        if data is not None:
            raise ValueError("Since a hparams file was specified via "
                             f"{'function arguments' if cli_f is None else 'the CLI'}, `data` must be None.")
        if isinstance(f, pathlib.PurePath):
            f = str(f)
        if isinstance(f, str):
            data = load_yaml_with_inheritance(f)
        else:
            data = yaml.full_load(f)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise TypeError("`data` must be a dict or None")

    try:
        hparams = _load(cls=cls,
                        data=data,
                        cli_args=remaining_cli_args,
                        prefix=[],
                        argparse_name_registry=argparse_name_registry,
                        argparsers=argparsers)
    except _MissingRequiredFieldException as e:
        _add_help(argparsers)
        raise ValueError("The following required fields were not included in the yaml nor the CLI arguments: "
                         f"{', '.join(e.args)}")
    else:
        _add_help(argparsers)

        # Only if successful, warn for extra cli arguments
        # If there is an error, then valid cli args may not have been discovered
        for arg in remaining_cli_args:
            if arg == sys.argv[0]:
                continue
            warnings.warn(f"ExtraArgumentWarning: {arg} was not used")

        return hparams
