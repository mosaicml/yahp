# YAHP: Yet Another HyperParameter

YAHP introduces a all-in-one hyperparameter management tool.

## Features:
* Utilizes [dataclasses](https://docs.python.org/3.8/library/dataclasses.html) to describe the data model.
* Supports `int`, `float`, `bool`, `str`, and `Enum`s; along with lists and nullable fields
* Fields can be optional (with a default) or required
* Auto-generates YAML templates, serializes the data model to YAML, and loads YAML into the data model.
* Nested field support, even with abstract classes
* Adds an [argparse](https://docs.python.org/3.8/library/argparse.html) CLI

## Getting Started

See the [simple example](examples/simple.py) for an example.
