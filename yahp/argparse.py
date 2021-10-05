from __future__ import annotations

import argparse
import collections.abc
import copy
from collections import defaultdict
from dataclasses import MISSING, fields
from enum import Enum
from typing import Any, Dict, List, Tuple, Type, get_type_hints

import yahp as hp
from yahp import type_helpers
from yahp.objects_helpers import ParserArgument
from yahp.types import JSON


def _str_to_bool(s: str, **kwargs) -> bool:
    if s.lower() in ['true', 't', 'yes', 'y', '1']:
        return True
    if s.lower() in ['false', 'f', 'no', 'n', '0']:
        return False
    raise Exception(f"Could not parse {s} as bool.")


def _retrieve_args(
    cls: Type[hp.Hparams],
    prefix: List[str],
    passed_args: Dict[str, Any],
) -> List[ParserArgument]:
    added_args = []
    type_hints = get_type_hints(cls)
    for field in fields(cls):
        ftype = type_hints[field.name]
        real_type = type_helpers._get_real_ftype(ftype)
        full_prefix = ".".join(prefix)
        if len(prefix):
            arg_name = f'--{full_prefix}.{field.name}'
        else:
            arg_name = f'--{field.name}'
        if 'doc' not in field.metadata:
            raise Exception(f"Please fill out documentation for the field: \n{field}")
        helptext = field.metadata['doc']

        required, default = type_helpers._get_required_default_from_field(field=field)
        type_name = type_helpers._get_type_name(ftype)
        if required:
            helptext = f'(required): <{type_name}> {helptext}'
        else:
            helptext = f'(default: {default}): <{type_name}>  {helptext}'

        parser_argument_default_kwargs = {
            "arg_type": real_type,
            "full_arg_name": arg_name,
            "helptext": helptext,
            "required": required,
        }
        # Assumes that if a field default is supposed to be None it will not appear in the namespace
        if type_helpers._is_hparams_type(type(default)):
            if field.name in cls.hparams_registry:
                inverted_field_registry = {v: k for (k, v) in cls.hparams_registry[field.name].items()}
                default = inverted_field_registry[type(default)]

        parser_argument_default_kwargs["default"] = default if default is not None else MISSING

        if type_helpers._is_enum_type(real_type):
            assert issubclass(real_type, Enum)
            parser_argument_default_kwargs["choices"] = [x.name.lower() for x in real_type]
            parser_argument_default_kwargs["arg_type"] = str
            new_arg = ParserArgument(**parser_argument_default_kwargs)
            added_args.append(new_arg)
        elif type_helpers._is_boolean_optional_type(ftype):
            parser_argument_default_kwargs["arg_type"] = _str_to_bool
            parser_argument_default_kwargs["nargs"] = "?"
            parser_argument_default_kwargs["const"] = True
            new_arg = ParserArgument(**parser_argument_default_kwargs)
            added_args.append(new_arg)
        elif type_helpers._is_list(ftype) and not type_helpers._is_hparams_type(real_type):
            parser_argument_default_kwargs["nargs"] = "+"
            new_arg = ParserArgument(**parser_argument_default_kwargs)
            added_args.append(new_arg)
        elif type_helpers._is_primitive_optional_type(ftype):
            new_arg = ParserArgument(**parser_argument_default_kwargs)
            added_args.append(new_arg)
        elif type_helpers._is_hparams_type(real_type):
            # Split into choose one
            if field.name not in cls.hparams_registry:
                # Defaults to direct nesting if missing from hparams_registry
                assert isinstance(real_type, type), f"{real_type} is not a class"
                assert issubclass(real_type, hp.Hparams), f"{real_type} is not a class"
                added_args += _retrieve_args(
                    cls=real_type,
                    prefix=prefix + [field.name],
                    passed_args=passed_args,
                )
            else:
                # Found in registry
                registry_entry = cls.hparams_registry[field.name]
                if isinstance(registry_entry, collections.abc.Mapping):
                    hparam_options = sorted(list(registry_entry.keys()))

                    parser_argument_default_kwargs["arg_type"] = str
                    if type_helpers._is_list(ftype):
                        # List Support
                        parser_argument_default_kwargs["nargs"] = "+"
                    parser_argument_default_kwargs["choices"] = hparam_options
                    parser_argument_default_kwargs["is_hparams_subclass"] = True
                    new_arg = ParserArgument(**parser_argument_default_kwargs)
                    added_args.append(new_arg)
                    if new_arg.get_namespace_name() in passed_args:
                        selected_subhparam = passed_args[new_arg.get_namespace_name()]
                        if isinstance(selected_subhparam, list):
                            for subhparam_selected in selected_subhparam:
                                subhparam_class: Type[hp.Hparams] = registry_entry[subhparam_selected]
                                added_args += _retrieve_args(
                                    cls=subhparam_class,
                                    prefix=prefix + [field.name, subhparam_selected],
                                    passed_args=passed_args,
                                )
                        elif isinstance(selected_subhparam, str):
                            subhparam_class: Type[hp.Hparams] = registry_entry[selected_subhparam]
                            added_args += _retrieve_args(
                                cls=subhparam_class,
                                prefix=prefix + [field.name, selected_subhparam],
                                passed_args=passed_args,
                            )
                # Direct listing
                elif type_helpers._is_hparams_type(registry_entry):
                    added_args += _retrieve_args(  # type: ignore
                        cls=registry_entry,
                        prefix=prefix + [field.name],
                        passed_args=passed_args,
                    )
    return added_args


def _add_short_arg_names_to_parser_argument_list(arg_list: List[ParserArgument],) -> List[ParserArgument]:
    #  Adds unique short argparse names if they exist, nesting if not, none if fully conflicted
    #  Shortness refers to how many nested layers deep arguments get shortened to
    short_name_dict = defaultdict(int)
    shortness_index = 0
    args_to_shorten = list(arg_list)
    while len(args_to_shorten):
        # Counts leaves for conflicts
        for arg_item in args_to_shorten:
            short_name_dict[arg_item.get_possible_short_name(index=shortness_index)] += 1
        done = []
        for arg_item in args_to_shorten:
            # If there is no conflict, shorten it
            if short_name_dict[arg_item.get_possible_short_name(index=shortness_index)] == 1:
                arg_item.short_arg_name = arg_item.get_possible_short_name(index=shortness_index)
                done.append(arg_item)
        for done_item in done:
            args_to_shorten.remove(done_item)

        # Increase the nesting factor for uniqueness
        shortness_index += 1
        if len(args_to_shorten):
            max_nesting = max([x.full_arg_name.count(".") for x in args_to_shorten])
            if shortness_index > max_nesting + 3:
                break

    # Fix formatting to ensure that -- prepends and no duplicate short names are added
    for args_item in arg_list:
        # prepend -- if not there
        if args_item.short_arg_name and not args_item.short_arg_name.startswith("--"):  # type: ignore
            args_item.short_arg_name = "--" + args_item.short_arg_name  # type: ignore
        if args_item.short_arg_name and args_item.short_arg_name == args_item.full_arg_name:  # type: ignore
            args_item.short_arg_name = None
    return arg_list


def _add_parser_argument_list_to_parser(arg_list: List[ParserArgument], parser_to_add: argparse.ArgumentParser) -> None:
    for arg_item in arg_list:
        add_argument_kwargs = {
            "type": arg_item.arg_type,
            "help": arg_item.helptext,
            "required": arg_item.required,
            "dest": arg_item.get_namespace_name(),
        }
        if arg_item.const:
            add_argument_kwargs["const"] = arg_item.const
        if arg_item.default != MISSING:
            add_argument_kwargs["default"] = arg_item.default
        if arg_item.choices:
            add_argument_kwargs["choices"] = arg_item.choices
        if arg_item.nargs:
            add_argument_kwargs["nargs"] = arg_item.nargs

        if arg_item.short_arg_name:
            # Encodes namespace with full path, but allows people to use short names for brevity
            parser_to_add.add_argument(
                arg_item.short_arg_name,
                arg_item.full_arg_name,
                **add_argument_kwargs,
            )
        else:
            parser_to_add.add_argument(
                arg_item.full_arg_name,
                **add_argument_kwargs,
            )


def _add_args(
    cls: Type[hp.Hparams],
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

    found_subparsers = 0
    found_subparser_args = dict()
    # This loop automagically recurses on runtime, creating parsers for found nested hparams
    # Allows nested Hparams to display their args
    # Iteratively runs a subparser over sub-hparam fields to determine if they are
    # selected in argparse
    # Allows for stuff like: ./main.py --optimizer sgd --help to include the sgd hparams object's helptext
    while True:
        all_args: List[ParserArgument] = _retrieve_args(
            cls=cls,
            prefix=prefix,
            passed_args=found_subparser_args,
        )
        subparser_args = [x for x in all_args if x.is_hparams_subclass]
        subparser_args = _add_short_arg_names_to_parser_argument_list(arg_list=subparser_args)
        for subparser_arg in subparser_args:
            subparser_arg.required = False
            # Use the subarguments in defaults to determine if a subparser has been selected
            subparser_namespace = subparser_arg.get_namespace_name()
            # TODO: Make robust to lists of subhparams
            unfiltered_nested_defaults = [x for x in defaults.keys() if x.startswith(subparser_namespace)]

            found_nested_defaults = set(
                [x[len(subparser_namespace) + 1:].split(".")[0] for x in unfiltered_nested_defaults])

            if "" in found_nested_defaults:
                found_nested_defaults.remove("")
            if subparser_arg.nargs == "+":
                defaults[subparser_namespace] = list(found_nested_defaults)
            else:
                if len(found_nested_defaults) == 1:
                    defaults[subparser_namespace] = found_nested_defaults.pop()

        hparams_subparser = argparse.ArgumentParser(add_help=False)
        hparams_subparser.set_defaults(**defaults)
        _add_parser_argument_list_to_parser(
            arg_list=subparser_args,
            parser_to_add=hparams_subparser,
        )

        # ignores unknown args (extra args a user may pass in)
        args, _ = hparams_subparser.parse_known_args()
        found_args_count = len([x for x in vars(args).values() if x])
        if found_args_count == found_subparsers:
            break
        found_subparsers = found_args_count
        found_subparser_args = {k: v for k, v in vars(args).items() if v is not None}

    all_args: List[ParserArgument] = _retrieve_args(
        cls=cls,
        prefix=prefix,
        passed_args=found_subparser_args,
    )
    all_args = _add_short_arg_names_to_parser_argument_list(arg_list=all_args)
    for arg in all_args:
        if arg.get_namespace_name() in defaults:
            arg.required = False
            arg.default = defaults[arg.get_namespace_name()]

    parser.set_defaults(**defaults)
    _add_parser_argument_list_to_parser(
        arg_list=all_args,
        parser_to_add=parser,
    )


def _yaml_data_to_argparse_namespace(
    yaml_data: Dict[str, Any],
    _prefix: List[str],
) -> Dict[str, Any]:
    items: Dict[str, Any] = dict()
    if len(yaml_data) == 0:
        full_path_name = ".".join(_prefix)
        items[full_path_name] = {}
        return items

    for key, val in yaml_data.items():
        if isinstance(val, collections.abc.Mapping):
            items.update(_yaml_data_to_argparse_namespace(
                yaml_data=val,  # type: ignore
                _prefix=_prefix + [key],
            ))
        else:
            full_path_name = ".".join(_prefix + [key])
            full_val = val
            if not isinstance(full_val, list):
                items[full_path_name] = full_val
            else:
                if not (len(full_val) and isinstance(full_val[0], collections.abc.Mapping)):
                    items[full_path_name] = full_val
                else:
                    # TODO: Fix this differentiation
                    # https://github.com/mosaicml/mosaicml/issues/147
                    likely_hparams = all([len(x) == 1 for x in full_val])
                    if not likely_hparams:
                        # Likely a direct json with a list of dicts
                        items[full_path_name] = full_val
                    else:
                        for sub_dict in full_val:
                            if sub_dict is None:
                                sub_dict = {}
                            sub_name = _yaml_data_to_argparse_namespace(
                                yaml_data=sub_dict,
                                _prefix=_prefix + [key],
                            )
                            items.update(sub_name)
    return items


def _namespace_to_hparams_dict(
    cls: Type[hp.Hparams],
    namespace: List[Tuple[str, Any]],
) -> Dict[str, Any]:
    """
    Converts an argparse namespace output back into the correct nested dict structure
    necessary to create an Hparams object

    This is necessary because argparse will flatten all arguments and lose information about
    all subhparams, so we need to use the class and introspect in order to reconstruct the correct
    data format

    This function is safe and does not do any validation as validation is done later
    """

    def sub_namespace(namespace_to_filter: List[Tuple[str, Any]], path: str):
        return [(x[len(path) + 1:], y) for (x, y) in namespace_to_filter if x.startswith(path)]

    def namespace_list_to_json_dict(namespace_list: List[Tuple[str, Any]]):
        res = dict()
        namespace_list = [(x.split("."), y) for (x, y) in namespace_list]  # type: ignore
        namespace_list = sorted(namespace_list, key=lambda x: len(x[0]))
        original_namespace_list = copy.deepcopy(namespace_list)
        filtered_namespace_list = [(x, y) for (x, y) in namespace_list if len(x) == 1]
        nested_namespace_list = [(x, y) for (x, y) in namespace_list if len(x) > 1]

        for keys, value in filtered_namespace_list:
            if keys[0] != "":
                res[keys[0]] = value

        nested_items = dict()
        for keys, value in nested_namespace_list:
            new_key = ".".join(keys[1:])
            if keys[0] in nested_items:
                nested_items[keys[0]].append((new_key, value))
            else:
                nested_items[keys[0]] = [(new_key, value)]

        for sub_dict, sub_dict_items in nested_items.items():
            res[sub_dict] = namespace_list_to_json_dict(namespace_list=sub_dict_items)

        return res

    res: Dict[str, JSON] = dict()
    namespace_dict: Dict[str, Any] = dict(namespace)  # for keying into results
    field_types = get_type_hints(cls)
    for f in fields(cls):
        ftype = field_types[f.name]
        if not (type_helpers._is_hparams_type(type_helpers._get_real_ftype(ftype))):
            # Not an hparam
            if not type_helpers._is_json_dict(ftype):
                if f.name in namespace_dict:
                    res[f.name] = namespace_dict[f.name]
            else:
                json_sub_namespace = sub_namespace(
                    namespace_to_filter=namespace,
                    path=f.name,
                )
                dict_data = namespace_list_to_json_dict(namespace_list=json_sub_namespace)
                res[f.name] = dict_data
        else:
            if type_helpers._is_list(ftype):
                selected_subhparams = namespace_dict[f.name]
                subhparams_list = []
                for selected_subhparam in selected_subhparams:
                    subhparam_namespace = sub_namespace(
                        namespace_to_filter=namespace,
                        path=f.name + "." + selected_subhparam,
                    )

                    subhparam_class = cls.hparams_registry.get(f.name, dict()).get(  # type: ignore
                        selected_subhparam,
                        None,
                    )
                    assert subhparam_class is not None, f"Unable to find subhparam in {cls.__name__} for field {f.name} and key {selected_subhparam}"
                    subhparams_list.append({
                        selected_subhparam:
                            _namespace_to_hparams_dict(
                                cls=subhparam_class,
                                namespace=subhparam_namespace,
                            )
                    })
                res[f.name] = subhparams_list
            else:
                # Directly nested vs choice
                if f.name not in cls.hparams_registry:
                    subhparam_namespace = sub_namespace(
                        namespace_to_filter=namespace,
                        path=f.name,
                    )
                    subhparam_class = type_helpers._get_real_ftype(ftype)
                    assert issubclass(subhparam_class, hp.Hparams)
                    res[f.name] = _namespace_to_hparams_dict(
                        cls=subhparam_class,
                        namespace=subhparam_namespace,
                    )
                else:
                    selected_subhparam = namespace_dict[f.name]
                    subhparam_namespace = sub_namespace(
                        namespace_to_filter=namespace,
                        path=f.name + "." + selected_subhparam,
                    )
                    subhparam_class = cls.hparams_registry.get(f.name, dict()).get(  # type: ignore
                        selected_subhparam,
                        None,
                    )
                    assert subhparam_class is not None, f"Unable to find subhparam in {cls.__name__} for field {f.name} and key {selected_subhparam}"
                    res[f.name] = {
                        selected_subhparam:
                            _namespace_to_hparams_dict(
                                cls=subhparam_class,
                                namespace=subhparam_namespace,
                            )
                    }
    return res
