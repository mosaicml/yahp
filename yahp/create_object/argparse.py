# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

import argparse
import logging
from dataclasses import _MISSING_TYPE, MISSING, asdict, dataclass, fields
from enum import Enum
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple, Union, get_type_hints

import yaml

import yahp as hp
from yahp.create_object.create_object import ensure_hparams_cls
from yahp.utils.type_helpers import HparamsType, get_default_value, is_field_required, safe_issubclass

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class ParserArgument:
    # ParserArgument represents an argument to add to argparse.
    full_name: str
    helptext: str
    nargs: Optional[str]
    choices: Optional[List[str]] = None
    short_name: Optional[str] = None

    def get_possible_short_names(self) -> List[str]:
        parts = self.full_name.split('.')
        ans: List[str] = []
        for i in range(len(parts)):
            ans.append('.'.join(parts[-(i + 1):]))
        return ans

    def __str__(self) -> str:
        return yaml.dump(asdict(self))

    def add_to_argparse(self, container: argparse._ActionsContainer) -> None:
        names = [f'--{self.full_name}']
        if self.short_name is not None and self.short_name != self.full_name:
            names.insert(0, f'--{self.short_name}')
        # not using argparse choices as they are too strict (e.g. case sensitive)
        metavar = self.full_name.split('.')[-1].upper()
        if self.choices is not None:
            metavar = f"{{{','.join(self.choices)}}}"
        container.add_argument(
            *names,
            nargs=self.nargs,  # type: ignore
            # using a sentinel to distinguish between a missing value and
            # a default value that could have been overridden in yaml
            default=MISSING,
            type=cli_parse,
            dest=self.full_name,
            const=True if self.nargs == '?' else None,
            # Replacing all % with %% to escape, so argparse does not attempt to
            # interpolate it with an argparse variable
            help=self.helptext.replace('%', '%%'),
            metavar=metavar,
        )


class ArgparseNameRegistry:
    # ArgparseNameRegistry tracks which names have already been used as argparse names to ensure no duplicates.
    def __init__(self) -> None:
        self._names: Set[str] = set()
        # tracks the shortname: possible args awaiting shortnames that could be assigned to it.
        self._shortnames: Dict[str, Set[ParserArgument]] = {}

    def reserve(self, *names: str) -> None:
        # Reserve names for non-parser-arguments
        for name in names:
            self._names.add(name)

    def add(self, *args: ParserArgument) -> None:
        # Add args to the registry
        for arg in args:
            if arg.full_name in self._names:
                raise ValueError(f'{arg.full_name} is already in the registry')
            self._names.add(arg.full_name)
            for shortname in arg.get_possible_short_names():
                if shortname not in self._shortnames:
                    self._shortnames[shortname] = set()
                self._shortnames[shortname].add(arg)

    def assign_shortnames(self):
        # Assign short names for args that do not already have shortnames
        #
        # It assigns the shortest name possible, while ensuring that if
        # multiple arguments (which have yet to get a shortname)
        # want the same shortname, then none get it.
        shortnames_list = list(self._shortnames.items())
        # sort the shortnames from longest to shortest
        shortnames_list.sort(key=lambda x: len(x[0]), reverse=True)

        while len(shortnames_list) > 0:
            # get the shortest shortname from the tail
            shortname, args = shortnames_list.pop()
            if shortname in self._names:
                # if the shortname is already taken (either as a long name,
                # or as a shortname from a previous call to assign_shortnames), then skip it
                continue
            if len(args) == 1:
                # Only one arg wants this shortname
                arg = list(args)[0]
                if arg.short_name is not None:
                    # This arg already has a shortname
                    # (e.g. a shorter shortname was available and is being used)
                    continue
                arg.short_name = shortname
                self._names.add(shortname)  # ensure it can't be used again by anything

    def __contains__(self, x: str) -> bool:
        return x in self._shortnames


def get_hparams_file_from_cli(
    *,
    cli_args: List[str],
    argparse_name_registry: ArgparseNameRegistry,
    argument_parsers: List[argparse.ArgumentParser],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    argument_parsers.append(parser)
    argparse_name_registry.reserve('f', 'file', 'd', 'dump', 'validate')
    parser.add_argument('-f',
                        '--file',
                        type=str,
                        default=None,
                        dest='file',
                        required=False,
                        help='Load data from this YAML file into the Hparams.')
    parser.add_argument(
        '-d',
        '--dump',
        type=str,
        const='stdout',
        nargs='?',
        default=None,
        required=False,
        metavar='stdout',
        help='Dump the resulting Hparams to the specified YAML file (defaults to `stdout`) and exit.',
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Whether to validate YAML against Hparams.',
    )
    parsed_args, cli_args[:] = parser.parse_known_args(cli_args)
    return parsed_args.file, parsed_args.dump, parsed_args.validate


def get_commented_map_options_from_cli(
    *,
    cli_args: List[str],
    argparse_name_registry: ArgparseNameRegistry,
    argument_parsers: List[argparse.ArgumentParser],
) -> Optional[Tuple[str, bool, bool]]:
    parser = argparse.ArgumentParser(add_help=False)
    argument_parsers.append(parser)

    argparse_name_registry.reserve('s', 'save_template', 'i', 'interactive', 'c', 'concise')

    parser.add_argument(
        '-s',
        '--save_template',
        type=str,
        const='stdout',
        nargs='?',
        default=None,
        required=False,
        metavar='stdout',
        help='Generate and dump a YAML template to the specified file (defaults to `stdout`) and exit.',
    )
    parser.add_argument(
        '-i',
        '--interactive',
        action='store_true',
        default=False,
        help='Whether to generate the template interactively. Only applicable if `--save_template` is present.',
    )
    parser.add_argument(
        '-c',
        '--concise',
        action='store_true',
        default=False,
        help='Skip adding documentation to the generated YAML. Only applicable if `--save_template` is present.',
    )

    parsed_args, cli_args[:] = parser.parse_known_args(cli_args)
    if parsed_args.save_template is None:
        return  # don't generate a template

    return parsed_args.save_template, parsed_args.interactive, not parsed_args.concise


def cli_parse(val: Union[str, _MISSING_TYPE]) -> Union[str, None, _MISSING_TYPE]:
    # Helper to parse CLI input
    # Almost like the default of `str`, but handles MISSING and "none" gracefully
    if val == MISSING:
        return val
    assert not isinstance(val, _MISSING_TYPE)
    if isinstance(val, str) and val.strip().lower() in ('', 'none'):
        return None
    return val


def retrieve_args(
    constructor: Callable,
    prefix: List[str],
    argparse_name_registry: ArgparseNameRegistry,
) -> Sequence[ParserArgument]:
    # Retrieve argparse args for the class. Does NOT recurse.

    # Create a dummy hparams class, and then parse from that
    cls = ensure_hparams_cls(constructor)
    field_types = get_type_hints(cls)
    ans: List[ParserArgument] = []

    for f in fields(cls):
        if not f.init:
            continue
        ftype = HparamsType(field_types[f.name])
        full_name = '.'.join(prefix + [f.name])
        type_name = str(ftype)
        helptext = f"<{type_name}> {f.metadata['doc']}"

        required = is_field_required(f)
        default = get_default_value(f)
        if required:
            helptext = f'(required): {helptext}'
        if default != MISSING:
            if default is None or safe_issubclass(type(default), (int, float, str, Enum)):
                helptext = f'{helptext} (Default: {default}).'
            elif safe_issubclass(type(default), hp.Hparams):
                helptext = f'{helptext} (Default: {type(default).__name__}).'

        # Assumes that if a field default is supposed to be None it will not appear in the namespace
        if safe_issubclass(type(default), hp.Hparams):
            # if the default is hparams, set the argparse default to the hparams registry key
            # for this hparams object
            if cls.hparams_registry is not None and f.name in cls.hparams_registry:
                inverted_field_registry = {v: k for (k, v) in cls.hparams_registry[f.name].items()}
                default = inverted_field_registry[type(default)]

        nargs = None
        if not ftype.is_recursive:
            if ftype.is_list:
                nargs = '*'
            elif ftype.is_boolean:
                nargs = '?'
            choices = None
            if ftype.is_enum:
                assert issubclass(ftype.type, Enum)
                choices = [x.name.lower() for x in ftype.type]
            if ftype.is_boolean and len(ftype.types) == 1:
                choices = ['true', 'false']
            if choices is not None and ftype.is_optional:
                choices.append('none')
            arg = ParserArgument(
                full_name=full_name,
                nargs=nargs,
                choices=choices,
                helptext=helptext,
            )
            ans.append(arg)
        else:
            # Split into choose one
            if cls.hparams_registry is None or f.name not in cls.hparams_registry:
                # Defaults to direct nesting if missing from hparams_registry
                if ftype.is_list:
                    # if it's a list of singletons, then print a warning and skip it
                    # Will use the default or yaml-provided value
                    logger.info('%s cannot be set via CLI arguments', full_name)
                elif ftype.is_optional:
                    # add a field to argparse that can be set to none to override the yaml (or default)
                    arg = ParserArgument(
                        full_name=full_name,
                        nargs=nargs,
                        helptext=helptext,
                    )
                    ans.append(arg)
            else:
                # Found in registry
                registry_entry = cls.hparams_registry[f.name]
                choices = sorted(list(registry_entry.keys()))
                if ftype.is_list:
                    nargs = '+' if required else '*'
                    required = False
                arg = ParserArgument(
                    full_name=full_name,
                    nargs=nargs,
                    choices=choices,
                    helptext=helptext,
                )
                ans.append(arg)
    argparse_name_registry.add(*ans)
    return ans
