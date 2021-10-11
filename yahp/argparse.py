from __future__ import annotations

import argparse
import logging
from dataclasses import _MISSING_TYPE, MISSING, InitVar, asdict, dataclass, fields
from enum import Enum
from typing import List, Optional, Sequence, Set, Tuple, Type, Union, get_type_hints

import yaml

import yahp as hp
from yahp.type_helpers import HparamsType, get_default_value, is_field_required, safe_issubclass

logger = logging.getLogger(__name__)


class ArgparseNameRegistry:
    """ArgparseNameRegistry tracks which names have already been used as argparse names to ensure no duplicates.
    """

    def __init__(self) -> None:
        self._names: Set[str] = set()

    def add(self, *names: str) -> None:
        """Add a name to the registry .

        Raises:
            ValueError: Raised if a `name` in :param names: is already in the registry.
        """
        for name in names:
            if name in self._names:
                raise ValueError(f"{name} is already in the registry")
            self._names.add(name)

    def reserve_shortnames(self, *args: _ParserArgument):
        """Reserve short names for argparse

        The order of :param args: is ignored. Short names are assigned deterministically, dependent
        on only the current state of the registry and the set of :class:`_ParserArgument`s in the function call.

        Args:
            args (_ParserArgument): :class:`_ParserArgument`s to assign short names

        """
        # sort args so short names get added deterministically
        sorted_args = sorted(args, key=lambda arg: arg.full_name)
        for arg in sorted_args:
            if arg.short_name is not None:
                raise ValueError(f"{arg.full_name} already has short name {arg.short_name}")
            for shortness_index in range(len(arg.full_name.split(".")) - 1):
                short_name = arg.get_possible_short_name(index=shortness_index)
                if short_name not in self:
                    self.add(short_name)
                    arg.short_name = short_name
                    break

    def __contains__(self, name: str) -> bool:
        return name in self._names


def get_hparams_file_from_cli(
    *,
    cli_args: List[str],
    argparse_name_registry: ArgparseNameRegistry,
    argument_parsers: List[argparse.ArgumentParser],
) -> Tuple[Optional[str], Optional[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    argument_parsers.append(parser)
    argparse_name_registry.add("f", "file", "d", 'dump')
    parser.add_argument("-f",
                        "--file",
                        type=str,
                        default=None,
                        dest='file',
                        required=False,
                        help="Load data from this YAML file into the Hparams.")
    parser.add_argument(
        "-d",
        "--dump",
        type=str,
        const="stdout",
        nargs="?",
        default=None,
        required=False,
        metavar="stdout",
        help="Dump the resulting Hparams to the specified YAML file (defaults to `stdout`) and exit.",
    )
    parsed_args, cli_args[:] = parser.parse_known_args(cli_args)
    return parsed_args.file, parsed_args.dump


def get_commented_map_options_from_cli(
    *,
    cli_args: List[str],
    argparse_name_registry: ArgparseNameRegistry,
    argument_parsers: List[argparse.ArgumentParser],
) -> Optional[Tuple[str, bool, bool]]:
    parser = argparse.ArgumentParser(add_help=False)
    argument_parsers.append(parser)

    argparse_name_registry.add("s", "save_template", "i", "interactive", "c", "concise")

    parser.add_argument(
        "-s",
        "--save_template",
        type=str,
        const="stdout",
        nargs="?",
        default=None,
        required=False,
        metavar="stdout",
        help="Generate and dump a YAML template to the specified file (defaults to `stdout`) and exit.",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        default=False,
        help="Whether to generate the template interactively. Only applicable if `--save_template` is present.",
    )
    parser.add_argument(
        "-c",
        "--concise",
        action="store_true",
        default=False,
        help="Skip adding documentation to the generated YAML. Only applicable if `--save_template` is present.",
    )

    parsed_args, cli_args[:] = parser.parse_known_args(cli_args)
    if parsed_args.save_template is None:
        return  # don't generate a template

    return parsed_args.save_template, parsed_args.interactive, not parsed_args.concise


@dataclass
class _ParserArgument:
    """_ParserArgument represents an argument to add to Argparse.
    """
    # if arg_type is None, then it should not have any entry in the argparse.
    # useful to represent its children
    argparse_name_registry: InitVar[ArgparseNameRegistry]
    full_name: str
    helptext: str
    nargs: Optional[str]
    choices: Optional[List[str]] = None
    short_name: Optional[str] = None

    def __post_init__(self, argparse_name_registry: ArgparseNameRegistry) -> None:
        # register the full name in argparse_name_registry
        argparse_name_registry.add(self.full_name)

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
            type=cli_parse,
            dest=self.full_name,
            const=True if self.nargs == "?" else None,
            help=self.helptext,
            metavar=metavar,
        )


def cli_parse(val: Union[str, _MISSING_TYPE]) -> Union[str, None, _MISSING_TYPE]:
    """Parse CLI input. This function is called internally by :module:`argparse`.

    Args:
        val: Argparse input.

    Returns:
        Union[str, None, _MISSING_TYPE]: Parsed value
    """
    if val == MISSING:
        return val
    assert not isinstance(val, _MISSING_TYPE)
    if isinstance(val, str) and val.strip().lower() in ("", "none"):
        return None
    return val


def retrieve_args(
    cls: Type[hp.Hparams],
    prefix: List[str],
    argparse_name_registry: ArgparseNameRegistry,
) -> Sequence[_ParserArgument]:
    """_retrieve_args retrieves the args in :param cls:. It does not recurse.

    Args:
        cls (Type[hp.Hparams]): The Hparams class
        prefix (List[str]): The path containing the keys from the top-level :class:`~yahp.Hparams` to :arg:`cls`
        parent_group (argparse._ActionsContainer): The :class:`argparse._ActionsContainer` to add a
            :class:`argparse._ArgumentGroup` for the :arg:`cls`
    Returns:
        A sequence of :class:`_ParserArgument` for this class. This is not computed recursively,
            to allow for lazily loading cli arguments.
    """
    field_types = get_type_hints(cls)
    ans: List[_ParserArgument] = []
    for f in fields(cls):
        if not f.init:
            continue
        ftype = HparamsType(field_types[f.name])
        full_name = ".".join(prefix + [f.name])
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
                _ParserArgument(
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
                        _ParserArgument(
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
                    _ParserArgument(
                        argparse_name_registry=argparse_name_registry,
                        full_name=full_name,
                        nargs=nargs,
                        choices=choices,
                        helptext=helptext,
                    ))
    return ans
