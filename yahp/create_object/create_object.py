# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys
import textwrap
import warnings
from dataclasses import MISSING, dataclass, fields
from typing import (TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, TextIO, Tuple, Type, TypeVar, Union,
                    cast, get_type_hints)

import yaml

from yahp.auto_hparams import ensure_hparams_cls
from yahp.create_object.argparse import (ArgparseNameRegistry, ParserArgument, get_commented_map_options_from_cli,
                                         get_hparams_file_from_cli, retrieve_args)
from yahp.hparams import Hparams
from yahp.inheritance import load_yaml_with_inheritance
from yahp.serialization import register_hparams_for_instance, register_hparams_registry_key_for_instance
from yahp.utils.iter_helpers import ensure_tuple, extract_only_item_from_dict, list_to_deduplicated_dict
from yahp.utils.type_helpers import HparamsType, get_default_value, is_field_required, is_none_like

if TYPE_CHECKING:
    from yahp.types import JSON, HparamsField

TObject = TypeVar('TObject')

__all__ = ['create', 'get_argparse']


class _MissingRequiredFieldException(ValueError):
    pass


@dataclass
class _DeferredCreateCall:
    constructor: Callable[..., Any]
    data: Dict[str, JSON]
    prefix: List[str]
    parser_args: Optional[Sequence[ParserArgument]]
    initialize: bool


def _get_split_key(key: str, splitter: str = '+') -> Tuple[str, Any]:
    """ Gets the prefix key and any label after the splitter """

    splits = key.split(splitter, 1)
    if len(splits) > 1:
        return (splits[0], splits[1])
    else:
        return (splits[0], None)


logger = logging.getLogger(__name__)


def _construct_object_from_deferred_create(
    create_call: _DeferredCreateCall,
    argparse_name_registry,
    parsed_arg_dict,
    argparsers: List[argparse.ArgumentParser],
    cli_args: Optional[List[str]],
    allow_recursion: bool,
):

    obj_hparams = _create(
        constructor=create_call.constructor,
        data=create_call.data,
        parsed_args=parsed_arg_dict,
        cli_args=cli_args,
        prefix=create_call.prefix,
        argparse_name_registry=argparse_name_registry,
        argparsers=argparsers,
        allow_recursion=allow_recursion,
    )
    if create_call.initialize:
        obj = obj_hparams.initialize_object()
    else:
        obj = obj_hparams

    if not isinstance(obj, Hparams):
        register_hparams_for_instance(obj, obj_hparams)

    return obj


def _create(
    *,
    constructor: Callable,
    data: Dict[str, JSON],
    parsed_args: Dict[str, str],
    cli_args: Optional[List[str]],
    prefix: List[str],
    argparse_name_registry: ArgparseNameRegistry,
    argparsers: List[argparse.ArgumentParser],
    allow_recursion: bool,
) -> Hparams:
    """Helper method that returns an instance of an hparams class from ``constructor``.

    *   If ``constructor`` is an :class:`.Hparams` class, then an instance of that hparams class is returned.
    *   Otherwise, an :class:`.Hparams` class will be dynamically generated. This dynamical class will have a
        :meth:`.initialize_object` that takes no arguments, and when invoked, calls and returns ``constructor``.

    Args:
        constructor (Type[Hparams]): The hparams class or a constructor
        data (Dict[str, JSON]):
            A JSON dictionary of values to use to initialize the class.
        parsed_args (Dict[str, str]):
            Parsed args for this class.
        cli_args (Optional[List[str]]):
            A list of cli args. This list is modified in-place,
            and all used arguments are removed from the list.
            Should be None if no cli args are to be used.
        prefix (List[str]):
            The prefix corresponding to the subset of ``cli_args``
            that should be used to instantiate this class.
        argparse_name_registry (_ArgparseNameRegistry):
            A registry to track CLI argument names.
        argparsers (List[argparse.ArgumentParser]):
            A list of :class:`~argparse.ArgumentParser` instances,
            which is extended in-place.
        allow_recursion (bool): Whether to recurse into sub-types if ``constructor`` is not a
            a subclass of :class:`.Hparams`. If ``false``, and the signautre of ``constructor``
            contains a non-primitive class, then a :exc:`TypeError` will be raised.
            Recursion is always allowed for :class:`.Hparams`.

    Returns:
        *   If ``constructor`` is an :class:`.Hparams` class, then an instance of that hparams class is returned.
        *   Otherwise, an :class:`.Hparams` class will be dynamically generated. This dynamical class will have a
            :meth:`.initialize_object` that takes no arguments, and when invoked, calls and returns ``constructor``.
    """
    # Heuristic:
    # If the constructor is from `typing`, `typing_extensions`, or `types`, then YAHP cannot instantiate
    # the object. Such type annotations are only supported when using a registry, and the registry contains
    # a class that implements the abstract type annotation
    if constructor.__module__ in ('typing', 'typing_extensions', 'types'):
        raise TypeError((f"Argument {'.'.join(prefix)} with type annotation {constructor} is abstract; however, "
                         'abstract types are not supported without the concrete implementations defined in the '
                         'hparams_registry.'))

    kwargs: Dict[str, HparamsField] = {}
    deferred_create_calls: Dict[str, Union[_DeferredCreateCall,  # singleton field
                                           List[_DeferredCreateCall],  # list field
                                          ]] = {}

    # keep track of missing required fields so we can build a nice error message
    missing_required_fields: List[str] = []

    # Convert the class to an hparams class if a constructor was passed in
    cls = ensure_hparams_cls(constructor)

    cls.validate_keys(list(data.keys()), allow_missing_keys=True)
    field_types = get_type_hints(cls)
    for f in fields(cls):
        if not f.init:
            continue
        prefix_with_fname = list(prefix) + [f.name]
        try:
            ftype = HparamsType(field_types[f.name])
            if not allow_recursion and not (isinstance(constructor, type) and issubclass(constructor, Hparams)):
                # If recursion is not allowed and it's not a hparams subclass
                # validate that ftype is primitive, json, enum, or an hparams subclass
                # This ensures that YAHP does not recurse through typing hell and generate an obsecure error message
                # about some super nested class having an unsupported field or missing annotation. Instead, if a user
                # is passing another class into the constructor, that is an advanced enough usage they should manually
                # create an Hparams or AutoInitializedHparams dataclass with a custom initialize object
                if ftype.is_recursive and not all(issubclass(x, Hparams) for x in ftype.types):
                    raise TypeError(
                        (f'Type annotation {ftype} for field {constructor.__name__}.{f.name} is not allowed. '
                         'For nested non-primitive types, please create a YAHP Hparams dataclass.'))

            full_name = '.'.join(prefix_with_fname)
            env_name = full_name.upper().replace('.', '_')  # dots are not (easily) allowed in env variables
            if full_name in parsed_args and parsed_args[full_name] != MISSING:
                # use CLI args first
                argparse_or_yaml_value = parsed_args[full_name]
            elif f.name in data:
                # then use YAML
                argparse_or_yaml_value = data[f.name]
            elif env_name in os.environ:
                # then use environment variables
                argparse_or_yaml_value = os.environ[env_name]
            else:
                # otherwise, set it as MISSING so the default will be used
                argparse_or_yaml_value = MISSING

            if not ftype.is_recursive:
                if argparse_or_yaml_value == MISSING:
                    if not is_field_required(f):
                        # if it's a primitive and there's a default value, use it
                        # do not attempt to auto-convert fields if the default value is not specified by the type annotations,
                        # as it may be a custom class or other sentential. Instead, let the static type checkers complain
                        default_value = get_default_value(f)
                        kwargs[f.name] = default_value
                    # if the field is required and not specified, then let the hparams constructor
                    # error
                else:
                    kwargs[f.name] = ftype.convert(argparse_or_yaml_value, full_name)
            else:
                # Dataclass or class constructor
                if cls.hparams_registry is None or f.name not in cls.hparams_registry:
                    # concrete, singleton hparams
                    # list of concrete hparams
                    # potentially none
                    if not ftype.is_list:
                        # concrete, singleton hparams
                        # potentially none. If cli args specify a child field, implicitly enable optional parent class
                        is_none = ftype.is_optional and is_none_like(argparse_or_yaml_value, allow_list=ftype.is_list)
                        if is_none and cli_args is not None:
                            # Likely pyright bug; hence the type ignore below
                            # Object of type "None" cannot be used as iterable value (reportOptionalIterable)
                            # Check to see if the cli args specify a child field. If so, implicitely enable the optional
                            # parent class
                            for cli_arg in cli_args:  # type: ignore
                                if cli_arg.lstrip('-').startswith(f.name):
                                    is_none = False
                                    break
                        if is_none:
                            # none
                            kwargs[f.name] = None
                        else:
                            # concrete, singleton hparams
                            sub_yaml = data.get(f.name)
                            if sub_yaml is None:
                                sub_yaml = {}
                            if not isinstance(sub_yaml, dict):
                                raise ValueError(f'{full_name} must be a dict in the yaml')
                            deferred_create_calls[f.name] = _DeferredCreateCall(
                                constructor=ftype.type,
                                data=sub_yaml,
                                prefix=prefix_with_fname,
                                parser_args=retrieve_args(
                                    constructor=ftype.type,
                                    prefix=prefix_with_fname,
                                    argparse_name_registry=argparse_name_registry,
                                ),
                                initialize=not (isinstance(ftype.type, type) and issubclass(ftype.type, Hparams)),
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
                            sub_yaml = data.get(f.name, [])

                            if isinstance(sub_yaml, dict):
                                # Deprecated syntax, where it is a dict of items. It should be a list of items
                                warnings.warn(
                                    DeprecationWarning(
                                        f"{'.'.join(prefix_with_fname)} should be a list, not a dictionary"))
                                sub_yaml = list(sub_yaml.values())

                            # check for and unpack phantom keys for backward compatability
                            if isinstance(sub_yaml, list):
                                # check all items in list are phantom keys. If old syntax is being used, verify it
                                # is used everywhere so we don't accidentally unpack a valid yaml based on this
                                # heuristic
                                is_list_of_phantom_keys = True
                                unpacked_sub_yaml = []
                                for sub_yaml_item in sub_yaml:
                                    # heuristic for phantom keys: single key dict with dict value
                                    if isinstance(sub_yaml_item, dict) and len(sub_yaml_item) == 1 and isinstance(
                                            list(sub_yaml_item.values())[0], dict):
                                        unpacked_sub_yaml.append(list(sub_yaml_item.values())[0])
                                    else:
                                        is_list_of_phantom_keys = False
                                        break
                                # unpack phantom keys
                                if is_list_of_phantom_keys:
                                    key_list = ', '.join([
                                        list(sub_yaml_item.keys())[0]
                                        for sub_yaml_item in sub_yaml
                                        if isinstance(sub_yaml_item, dict)
                                    ])
                                    warnings.warn(
                                        DeprecationWarning(
                                            f'Ignoring the following keys: {key_list}. When specifying an object in a yaml, the object should be directly encoded instead of adding a phantom key. See https://stackoverflow.com/questions/33989612/yaml-equivalent-of-array-of-objects-in-json for an extended explanation.'
                                        ))
                                    sub_yaml = unpacked_sub_yaml

                            if not isinstance(sub_yaml, list):
                                raise TypeError(f'{full_name} must be a list in the yaml')

                            deferred_calls: List[_DeferredCreateCall] = []
                            for i, sub_yaml_item in enumerate(sub_yaml):
                                if sub_yaml_item is None:
                                    sub_yaml_item = {}
                                if not isinstance(sub_yaml_item, dict):
                                    raise TypeError(f'{full_name} must be a dict in the yaml')
                                assert issubclass(ftype.type, Hparams)
                                deferred_calls.append(
                                    _DeferredCreateCall(
                                        constructor=ftype.type,
                                        data=sub_yaml_item,
                                        prefix=prefix_with_fname + [str(i)],
                                        parser_args=None,
                                        initialize=not (isinstance(ftype.type, type) and
                                                        issubclass(ftype.type, Hparams)),
                                    ))
                            deferred_create_calls[f.name] = deferred_calls
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
                                raise ValueError(f'Field {full_name} is required and cannot be None.')
                            if isinstance(argparse_or_yaml_value, str):
                                key = argparse_or_yaml_value
                            else:
                                if not isinstance(argparse_or_yaml_value, dict):
                                    raise ValueError(
                                        f'Field {full_name} must be a dict with just one key if specified in the yaml')
                                try:
                                    key, _ = extract_only_item_from_dict(argparse_or_yaml_value)
                                except ValueError as e:
                                    raise ValueError(f'Field {full_name} ' + e.args[0])
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
                            deferred_create_calls[f.name] = _DeferredCreateCall(
                                constructor=cls.hparams_registry[f.name][key],
                                prefix=prefix_with_fname + [key],
                                data=yaml_val,
                                parser_args=retrieve_args(
                                    constructor=cls.hparams_registry[f.name][key],
                                    prefix=prefix_with_fname + [key],
                                    argparse_name_registry=argparse_name_registry,
                                ),
                                initialize=not (isinstance(ftype.type, type) and issubclass(ftype.type, Hparams)),
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
                            # Argparse has precedence. If there are keys defined in argparse, use only those
                            # These keys will determine what is loaded
                            if argparse_or_yaml_value is None:
                                raise ValueError(f'Field {full_name} is required and cannot be None.')
                            if isinstance(argparse_or_yaml_value, list):
                                # Convert from list of single element dictionaries to dict, preserving duplicates
                                argparse_or_yaml_value = list_to_deduplicated_dict(argparse_or_yaml_value,
                                                                                   allow_str=True)

                            if not isinstance(argparse_or_yaml_value, dict):
                                raise ValueError(f'Field {full_name} should be a dict')

                            keys = list(argparse_or_yaml_value.keys())

                            # Now, load the values for these keys
                            yaml_val = data.get(f.name)
                            if yaml_val is None:
                                yaml_val = {}
                            if isinstance(yaml_val, list):
                                yaml_val = list_to_deduplicated_dict(yaml_val)
                            if not isinstance(yaml_val, dict):
                                raise ValueError(
                                    f"Field {'.'.join(prefix_with_fname)} must be a dict if specified in the yaml")

                            deferred_calls: List[_DeferredCreateCall] = []

                            for key in keys:
                                # Use the order of keys
                                key_yaml = yaml_val.get(key)
                                if key_yaml is None:
                                    key_yaml = {}
                                if not isinstance(key_yaml, dict):
                                    raise ValueError(
                                        textwrap.dedent(f"""Field {'.'.join(prefix_with_fname + [key])}
                                        must be a dict if specified in the yaml"""))
                                split_key, _ = _get_split_key(key)
                                deferred_calls.append(
                                    _DeferredCreateCall(
                                        constructor=cls.hparams_registry[f.name][split_key],
                                        prefix=prefix_with_fname + [key],
                                        data=key_yaml,
                                        parser_args=retrieve_args(
                                            constructor=cls.hparams_registry[f.name][split_key],
                                            prefix=prefix_with_fname + [key],
                                            argparse_name_registry=argparse_name_registry,
                                        ),
                                        initialize=not (isinstance(ftype.type, type) and
                                                        issubclass(ftype.type, Hparams)),
                                    ))
                            deferred_create_calls[f.name] = deferred_calls
        except _MissingRequiredFieldException as e:
            missing_required_fields.extend(e.args)
            # continue processing the other fields and gather everything together

    allow_recursion = isinstance(constructor, type) and issubclass(constructor, Hparams)

    if cli_args is None:
        for fname, create_calls in deferred_create_calls.items():
            registry = None
            if cls.hparams_registry is not None and fname in cls.hparams_registry:
                registry = cls.hparams_registry[fname]
                inverted_registry = {v: k for (k, v) in registry.items()}
            else:
                inverted_registry = {}
            sub_hparams = []
            for create_call in ensure_tuple(create_calls):
                obj = _construct_object_from_deferred_create(
                    create_call=create_call,
                    argparse_name_registry=argparse_name_registry,
                    parsed_arg_dict={},
                    argparsers=argparsers,
                    cli_args=cli_args,
                    allow_recursion=allow_recursion,
                )

                sub_hparams.append(obj)
                if registry is not None:
                    register_hparams_registry_key_for_instance(
                        obj,
                        registry,
                        inverted_registry[create_call.constructor],
                    )

            if isinstance(create_calls, list):
                kwargs[fname] = sub_hparams
            else:
                kwargs[fname] = sub_hparams[0]
    else:
        all_args: List[ParserArgument] = []
        for fname, create_calls in deferred_create_calls.items():
            for create_call in ensure_tuple(create_calls):
                if create_call.parser_args is not None:
                    all_args.extend(create_call.parser_args)
        argparse_name_registry.assign_shortnames()
        for fname, create_calls in deferred_create_calls.items():
            # TODO parse args from
            registry = None
            if cls.hparams_registry is not None and fname in cls.hparams_registry:
                registry = cls.hparams_registry[fname]
                inverted_registry = {v: k for (k, v) in registry.items()}
            else:
                inverted_registry = {}
            sub_hparams: List[Hparams] = []
            for create_call in ensure_tuple(create_calls):
                if create_call.parser_args is None:
                    parsed_arg_dict = {}
                else:
                    parser = argparse.ArgumentParser(add_help=False)
                    argparsers.append(parser)
                    group = parser.add_argument_group(title='.'.join(create_call.prefix),
                                                      description=create_call.constructor.__name__)
                    for args in create_call.parser_args:
                        for arg in ensure_tuple(args):
                            arg.add_to_argparse(group)
                    parsed_arg_namespace, cli_args[:] = parser.parse_known_args(cli_args)
                    parsed_arg_dict = vars(parsed_arg_namespace)
                obj = _construct_object_from_deferred_create(
                    create_call=create_call,
                    argparse_name_registry=argparse_name_registry,
                    parsed_arg_dict=parsed_arg_dict,
                    argparsers=argparsers,
                    cli_args=cli_args,
                    allow_recursion=allow_recursion,
                )
                sub_hparams.append(obj)
                if registry is not None:
                    register_hparams_registry_key_for_instance(sub_hparams[-1], registry,
                                                               inverted_registry[create_call.constructor])
            if isinstance(create_calls, list):
                kwargs[fname] = sub_hparams
            else:
                kwargs[fname] = sub_hparams[0]

    for f in fields(cls):
        if not f.init:
            continue
        prefix_with_fname = '.'.join(list(prefix) + [f.name])
        if f.name not in kwargs:
            if f.default == MISSING and f.default_factory == MISSING:
                missing_required_fields.append(prefix_with_fname)
    if len(missing_required_fields) > 0:
        # if there are any missing fields from this class, or optional but partially-filled-in subclasses,
        # then propegate back the missing fields
        raise _MissingRequiredFieldException(*missing_required_fields)

    return cls(**kwargs)


def _add_help(argparsers: Sequence[argparse.ArgumentParser], cli_args: Sequence[str]) -> None:
    """Add an :class:`~argparse.ArgumentParser` that adds help.

    Args:
        argparsers (Sequence[argparse.ArgumentParser]): List of :class:`~argparse.ArgumentParser`s
            to extend.
    """
    help_argparser = argparse.ArgumentParser(parents=argparsers)
    help_argparser.parse_known_args(args=cli_args)  # Will print help and exit if the "--help" flag is present


def _get_remaining_cli_args(cli_args: Union[List[str], bool]) -> List[str]:
    if cli_args is True:
        return sys.argv[1:]  # remove the program name
    if cli_args is False:
        return []
    return list(cli_args)


def create(
    constructor: Callable[..., TObject],
    data: Optional[Dict[str, JSON]] = None,
    f: Union[str, TextIO, pathlib.PurePath, None] = None,
    cli_args: Union[List[str], bool] = True,
) -> TObject:
    """Create a class or invoke a function with arguments coming from a dictionary, YAML string or file, or the CLI.

    This function is the main entrypoint to YAHP! It will recurse through the configuration -- which can come from
    CLI args or a JSON dictionary, or YAML file -- to invoke the ``constructor``. For example:

    .. testcode::

        import yahp as hp

        class Foo:
            '''Foo Docstring

            Args:
                arg (int): Integer variable.
            '''

            def __init__(self, arg: int):
                self.arg = arg

    .. doctest::

        >>> foo_instance = hp.create(Foo, data={'arg': 42})
        >>> foo_instance.arg
        42

    The ``constructor`` can also have nested classes:

    .. testcode::

        import yahp as hp

        class Bar:
            '''Bar Docstring

            Args:
                foo (Foo): Foo class
            '''

            def __init__(self, foo: Foo):
                self.foo = foo

    .. doctest::

        >>> bar_instance = hp.create(Bar, data={'foo': {'arg': 42}})
        >>> bar_instance.foo.arg
        42

    Args:
        constructor (type | callable): Class or function.

            If a class is provided, an instance of the class will be returned.
            If a function is provided, the resulting value from the function will be returned.

            The arguments used to construct the class or invoke the function come from ``data``, ``f``,
            and/or ``cli_args``.
        f (Union[str, None, TextIO, pathlib.PurePath], optional):
            If specified, load values from a YAML file.
            Can be either a filepath or file-like object.
            Cannot be specified with ``data``.
        data (Optional[Dict[str, JSON]], optional): Data dictionary.

            If specified, this dictionary will be used for
            the :class:`~yahparams.Hparams`. Cannot be specified with ``f``.
        cli_args (Union[List[str], bool], optional): CLI argument overrides.
            Can either be a list of CLI argument,
            True (the default) to load CLI arguments from ``sys.argv``,
            or False to not use any CLI arguments.

    Returns:
        The constructed object.
    """
    argparsers: List[argparse.ArgumentParser] = []
    remaining_cli_args = _get_remaining_cli_args(cli_args)
    try:
        hparams, output_f = _get_hparams(constructor=constructor,
                                         data=data,
                                         f=f,
                                         remaining_cli_args=remaining_cli_args,
                                         argparsers=argparsers)
    except _MissingRequiredFieldException as e:
        _add_help(argparsers, remaining_cli_args)
        missing_fields = f"{', '.join(e.args)}"
        raise ValueError(
            f'The following required fields were not included in the yaml nor the CLI arguments: {missing_fields}'
        ) from e
    _add_help(argparsers, remaining_cli_args)

    # Only if successful, warn for extra cli arguments
    # If there is an error, then valid cli args may not have been discovered
    for arg in remaining_cli_args:
        warnings.warn(f'ExtraArgumentWarning: {arg} was not used')

    if output_f is not None:
        if output_f == 'stdout':
            print(hparams.to_yaml(), file=sys.stdout)
        elif output_f == 'stderr':
            print(hparams.to_yaml(), file=sys.stderr)
        else:
            with open(output_f, 'x') as f:
                f.write(hparams.to_yaml())
        sys.exit(0)

    if isinstance(constructor, type) and issubclass(constructor, Hparams):
        return cast(TObject, hparams)
    else:
        constructed_obj = hparams.initialize_object()
        register_hparams_for_instance(constructed_obj, hparams)
        return constructed_obj


def _get_hparams(
    constructor: Union[Type[TObject], Callable[..., TObject]],
    data: Optional[Dict[str, JSON]],
    f: Union[str, TextIO, pathlib.PurePath, None],
    remaining_cli_args: List[str],
    argparsers: List[argparse.ArgumentParser],
) -> Tuple[Hparams, Optional[str]]:
    argparse_name_registry = ArgparseNameRegistry()

    cm_options = get_commented_map_options_from_cli(
        cli_args=remaining_cli_args,
        argparse_name_registry=argparse_name_registry,
        argument_parsers=argparsers,
    )
    if cm_options is not None:
        output_file, interactive, add_docs = cm_options
        print(f'Generating a template for {constructor.__name__}...')
        cls = ensure_hparams_cls(constructor)
        if output_file == 'stdout':
            cls.dump(add_docs=add_docs, interactive=interactive, output=sys.stdout)
        elif output_file == 'stderr':
            cls.dump(add_docs=add_docs, interactive=interactive, output=sys.stderr)
        else:
            with open(output_file, 'x') as f:
                cls.dump(add_docs=add_docs, interactive=interactive, output=f)
        # exit so we don't attempt to parse and instantiate if generate template is passed
        print('\nFinished')
        sys.exit(0)

    cli_f, output_f, validate = get_hparams_file_from_cli(cli_args=remaining_cli_args,
                                                          argparse_name_registry=argparse_name_registry,
                                                          argument_parsers=argparsers)

    if cli_f is not None:
        if f is not None:
            raise ValueError('File cannot be specified via both function arguments and the CLI')
        f = cli_f

    # Validate was specified, so only validate instead of instantiating
    if validate:
        print(f'Validating YAML against {constructor.__name__}...')
        cls = ensure_hparams_cls(constructor)
        cls.validate_yaml(f=f)
        # exit so we don't attempt to parse and instantiate
        print('\nSuccessfully validated YAML!')
        sys.exit(0)

    if f is not None:
        if data is not None:
            raise ValueError(
                textwrap.dedent(f"""Since a hparams file was specified via
                {'function arguments' if cli_f is None else 'the CLI'}, `data` must be None."""))
        if isinstance(f, pathlib.PurePath):
            f = str(f)
        if isinstance(f, str):
            data = load_yaml_with_inheritance(f)
        else:
            data = yaml.full_load(f)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise TypeError('`data` must be a dict or None')

    # Parse args based on class definition
    main_args = retrieve_args(constructor=constructor, prefix=[], argparse_name_registry=argparse_name_registry)
    parser = argparse.ArgumentParser(add_help=False)
    argparsers.append(parser)
    group = parser.add_argument_group(title=constructor.__name__)
    for arg in main_args:
        arg.add_to_argparse(group)
    parsed_arg_namespace, remaining_cli_args[:] = parser.parse_known_args(remaining_cli_args)
    parsed_arg_dict = vars(parsed_arg_namespace)

    hparams = _create(
        constructor=constructor,
        data=data,
        cli_args=remaining_cli_args,
        prefix=[],
        parsed_args=parsed_arg_dict,
        argparse_name_registry=argparse_name_registry,
        argparsers=argparsers,
        allow_recursion=True,
    )
    return hparams, output_f


def get_argparse(
    constructor: Union[Type[TObject], Callable[..., TObject]],
    data: Optional[Dict[str, JSON]] = None,
    f: Union[str, TextIO, pathlib.PurePath, None] = None,
    cli_args: Union[List[str], bool] = True,
) -> argparse.ArgumentParser:
    """Get an :class:`~argparse.ArgumentParser` containing all CLI arguments.

    It is usually not necessary to manually parse the CLI args, as :func:`.create` will do that automatically.
    However, if you have additional CLI arguments, then it is recommended to use this function to get a
    :class:`~argparse.ArgumentParser` instance to ensure that ``--help`` will show all CLI arguments.

    For example:

    .. testcode::

        import yahp as hp

        class MyClass:
            '''MyClass Docstring

            Args:
                foo (int): Foo
            '''

            def __init__(self, foo: int):
                self.foo = foo

        # Get the parser
        parser = hp.get_argparse(MyClass)

        # Add additional arguments
        parser.add_argument(
            '--my_argument',
            type=str,
            help='Additional, non-YAHP argument',
        )

    The ``--my_argument`` is accessible like normal:

    .. doctest::

        >>> cli_args = ['--foo', '42', '--my_argument', 'Hello, world!']
        >>> args = parser.parse_args(cli_args)
        >>> args.my_argument
        'Hello, world!'

    And :func:`.create` would still work, ignoring the custom ``--my_argument``:

    .. doctest::

        >>> my_instance = hp.create(MyClass, cli_args=['--foo', '42'])
        >>> my_instance.foo
        42

    Args:
        constructor (type | callable): Class or function.

            If a subclass of :class:`.Hparams` is provided, then the CLI arguments will match the
            fields of the hyperameter class.

            Otherwise, if a generic class or function is provided, then the arguments, default values,
            and help text come from docstring and constructor (or function) signature.
        f (str | TextIO | pathlib.Path, optional): If specified, load values from a YAML file.
            Can be either a filepath or file-like object. Cannot be specified with ``data``.
        data (Optional[Dict[str, JSON]], optional):
            f specified, uses this dictionary for instantiating
            the :class:`~yahparams.Hparams`. Cannot be specified with ``f``.
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
        _get_hparams(
            constructor=constructor,
            data=data,
            f=f,
            remaining_cli_args=remaining_cli_args,
            argparsers=argparsers,
        )
    except _MissingRequiredFieldException:
        pass
    helpless_parent_argparse = argparse.ArgumentParser(add_help=False, parents=argparsers)
    return helpless_parent_argparse
