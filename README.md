# YAHP: Yet Another HyperParameter

YAHP introduces yet another hyperparameter management tool.

## Features
* Utilizes [dataclasses](https://docs.python.org/3.8/library/dataclasses.html) to describe the data model.
* Supports `int`, `float`, `bool`, `str`, and `Enum`s; along with lists and nullable fields
* Fields can be optional (with a default) or required
* Auto-generates YAML templates, serializes the data model to YAML, and loads YAML into the data model.
* Allows for nested dataclasses -- even with abstract classes
* Adds an [argparse](https://docs.python.org/3.8/library/argparse.html) CLI

## Getting Started

* See the [simple example](examples/simple) for a simple data model and yaml file.
* See the [cli example](examples/cli) for an example of the CLI.
* See the [registry example](examples/registry) for how to use nested dataclasses with inheritance.

## YAHP Command Line
Whenever `Hparams.create()` is invoked, YAHP adds the following command line options:

* `-h`, `--help`: Print help and exit.
* `-f`, `--file`": Load data from this YAML file into the Hparams.
* `-s`, `--save_template`: Generate and dump a YAML template to the specified file (defaults to `stdout`) and exit.
* `-i`, `--interactive`: Whether to generate the template interactively. Only applicable if `--save_template` is present.
*  `-c`, `--concise`: Skip adding documentation to the generated YAML. Only applicable if `--save_template` is present.
*  `-d`, `--dump`: Dump the resulting Hparams to the specified YAML file (defaults to `stdout`) and exit.
