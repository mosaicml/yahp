from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys
import warnings
from dataclasses import _MISSING_TYPE, MISSING, fields
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, TextIO, Tuple, Type, Union, get_type_hints

import yaml

import yahp as hp
from yahp.argparse import (ArgparseNameRegistry, get_commented_map_options_from_cli, get_hparams_file_from_cli,
                           retrieve_args)
from yahp.inheritance import load_yaml_with_inheritance
from yahp.type_helpers import HparamsType, is_none_like
from yahp.utils import extract_only_item_from_dict

if TYPE_CHECKING:
    from yahp.types import JSON, HparamsField, THparams


class _MissingRequiredFieldException(ValueError):
    pass


def _emit_should_be_list_warning(arg_name: str):
    warnings.warn(f"MalformedYAMLWarning: {arg_name} should be a list, not a singular element.")


logger = logging.getLogger(__name__)


def _create(
    *,
    cls: Type[THparams],
    data: Dict[str, JSON],
    cli_args: Optional[List[str]],
    prefix: List[str],
    argparse_name_registry: ArgparseNameRegistry,
    argparsers: List[argparse.ArgumentParser],
) -> THparams:
    """Helper method to recursively create an instance of :param cls:. It should not be called directly

    Args:
        cls (Type[THparams]): A :class:`~yahp.Hparams` to create.
        data (Dict[str, JSON]): A JSON dictionary of values to use to initialize :param cls:.
        cli_args (Optional[List[str]]): A list of cli args. This list is modified in-place, and all used arguments
            are removed from the list.
        prefix (List[str]): The prefix for the :param cli_args: that should be used to instantiate this class.
        argparse_name_registry (_ArgparseNameRegistry): A registry to track CLI argument names
        argparsers (List[argparse.ArgumentParser]): A list of :class:`~argparse.ArgumentParser`s,
            which is extended in-place.

    Returns:
        THparams: An instance of :param cls:
    """
    if cli_args is None:
        parsed_arg_dict = {}
    else:
        args = retrieve_args(cls, prefix, argparse_name_registry)
        argparse_name_registry.reserve_shortnames(*args)
        parser = argparse.ArgumentParser(add_help=False)
        group = parser
        if len(prefix):
            group = parser.add_argument_group(title=".".join(prefix), description=cls.__name__)
        for arg in args:
            arg.add_to_argparse(group)
        parsed_arg_namespace, cli_args[:] = parser.parse_known_args(cli_args)
        parsed_arg_dict = vars(parsed_arg_namespace)
        argparsers.append(parser)
    kwargs: Dict[str, HparamsField] = {}

    # keep track of missing required fields so we can build a nice error message
    missing_required_fields: List[str] = []

    cls.validate_keys(list(data.keys()), allow_missing_keys=True)
    field_types = get_type_hints(cls)
    for f in fields(cls):
        if not f.init:
            continue
        prefix_with_fname = list(prefix) + [f.name]
        try:
            ftype = HparamsType(field_types[f.name])
            full_name = ".".join(prefix_with_fname)
            argparse_or_yaml_value: Union[_MISSING_TYPE, JSON] = MISSING
            if full_name in parsed_arg_dict and parsed_arg_dict[full_name] != MISSING:
                argparse_or_yaml_value = parsed_arg_dict[full_name]
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
                            kwargs[f.name] = _create(
                                cls=ftype.type,
                                data=sub_yaml,
                                prefix=prefix_with_fname,
                                cli_args=cli_args,
                                argparse_name_registry=argparse_name_registry,
                                argparsers=argparsers,
                            )
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
                                sub_hparams = _create(
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
                            kwargs[f.name] = _create(
                                cls=cls.hparams_registry[f.name][key],
                                prefix=prefix_with_fname + [key],
                                data=yaml_val,
                                cli_args=cli_args,
                                argparse_name_registry=argparse_name_registry,
                                argparsers=argparsers,
                            )
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
                                sub_hparams = _create(
                                    cls=cls.hparams_registry[f.name][key],
                                    prefix=prefix_with_fname + [key],
                                    data=key_yaml,
                                    cli_args=cli_args,
                                    argparse_name_registry=argparse_name_registry,
                                    argparsers=argparsers,
                                )
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
    """Add an :class:`~argparse.ArgumentParser` that adds help.

    Args:
        argparsers (Sequence[argparse.ArgumentParser]): List of :class:`~argparse.ArgumentParser`s
            to extend.
    """
    help_argparser = argparse.ArgumentParser(parents=argparsers)
    help_argparser.parse_known_args()  # Will print help and exit if the "--help" flag is present


def _get_remaining_cli_args(cli_args: Union[List[str], bool]) -> List[str]:
    if cli_args is True:
        return sys.argv[1:]  # remove the program name
    if cli_args is False:
        return []
    return list(cli_args)


def create(
    cls: Type[THparams],
    data: Optional[Dict[str, JSON]] = None,
    f: Union[str, TextIO, pathlib.PurePath, None] = None,
    cli_args: Union[List[str], bool] = True,
) -> THparams:
    """Create a instance of :class:`~yahp.Hparams`.

    Args:
        f (Union[str, None, TextIO, pathlib.PurePath], optional):
            If specified, load values from a YAML file.
            Can be either a filepath or file-like object.
            Cannot be specified with :param data:.
        data (Optional[Dict[str, JSON]], optional): 
            f specified, uses this dictionary for instantiating
            the :class:`~yahp.Hparams`. Cannot be specified with :param f:.
        cli_args (Union[List[str], bool], optional): CLI argument overrides.
            Can either be a list of CLI argument,
            `true` (the default) to load CLI arguments from `sys.argv`,
            or `false` to not use any CLI arguments.

    Returns:
        THparams: An instance of :class:`~yahp.Hparams`.
    """
    argparsers: List[argparse.ArgumentParser] = []
    remaining_cli_args = _get_remaining_cli_args(cli_args)
    try:
        hparams, output_f = _get_hparams(cls=cls,
                                         data=data,
                                         f=f,
                                         remaining_cli_args=remaining_cli_args,
                                         argparsers=argparsers)
    except _MissingRequiredFieldException as e:
        _add_help(argparsers)
        raise ValueError("The following required fields were not included in the yaml nor the CLI arguments: "
                         f"{', '.join(e.args)}") from e
    _add_help(argparsers)

    # Only if successful, warn for extra cli arguments
    # If there is an error, then valid cli args may not have been discovered
    for arg in remaining_cli_args:
        warnings.warn(f"ExtraArgumentWarning: {arg} was not used")

    if output_f is not None:
        if output_f == "stdout":
            print(hparams.to_yaml(), file=sys.stdout)
        elif output_f == "stderr":
            print(hparams.to_yaml(), file=sys.stderr)
        else:
            with open(output_f, "x") as f:
                f.write(hparams.to_yaml())
        sys.exit(0)

    return hparams


def _get_hparams(
    cls: Type[THparams],
    data: Optional[Dict[str, JSON]],
    f: Union[str, TextIO, pathlib.PurePath, None],
    remaining_cli_args: List[str],
    argparsers: List[argparse.ArgumentParser],
) -> Tuple[THparams, Optional[str]]:
    argparse_name_registry = ArgparseNameRegistry()

    cm_options = get_commented_map_options_from_cli(
        cli_args=remaining_cli_args,
        argparse_name_registry=argparse_name_registry,
        argument_parsers=argparsers,
    )
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

    cli_f, output_f = get_hparams_file_from_cli(cli_args=remaining_cli_args,
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

    return _create(cls=cls,
                   data=data,
                   cli_args=remaining_cli_args,
                   prefix=[],
                   argparse_name_registry=argparse_name_registry,
                   argparsers=argparsers), output_f


def get_argparse(
    cls: Type[THparams],
    data: Optional[Dict[str, JSON]] = None,
    f: Union[str, TextIO, pathlib.PurePath, None] = None,
    cli_args: Union[List[str], bool] = True,
) -> argparse.ArgumentParser:
    """Get an :class:`~argparse.ArgumentParser` containing all CLI arguments.

    Args:
        f (Union[str, None, TextIO, pathlib.PurePath], optional):
            If specified, load values from a YAML file.
            Can be either a filepath or file-like object.
            Cannot be specified with :param data:.
        data (Optional[Dict[str, JSON]], optional): 
            f specified, uses this dictionary for instantiating
            the :class:`~yahp.Hparams`. Cannot be specified with :param f:.
        cli_args (Union[List[str], bool], optional): CLI argument overrides.
            Can either be a list of CLI argument,
            `true` (the default) to load CLI arguments from `sys.argv`,
            or `false` to not use any CLI arguments.

    Returns:
        argparse.ArgumentParser: An argparser with all CLI arguments, but without any help.
    """
    argparsers: List[argparse.ArgumentParser] = []

    remaining_cli_args = _get_remaining_cli_args(cli_args)

    try:
        _get_hparams(cls=cls, data=data, f=f, remaining_cli_args=remaining_cli_args, argparsers=argparsers)
    except _MissingRequiredFieldException:
        pass
    helpless_parent_argparse = argparse.ArgumentParser(add_help=False, parents=argparsers)
    return helpless_parent_argparse
