CLI
===

In addition to loading from YAML, YAHP also supports loading data from
CLI arguments.

Consider the following YAML called ``cli.yaml``:

.. literalinclude:: ../../../examples/cli/cli.yaml


Now, consider the following script called ``cli.py`` that defines the
:class:`~yahp.hparams.Hparams` and loads this YAML file:

.. literalinclude:: ../../../examples/cli/cli.py
    :linenos:


If you were to run ``python cli.py``, YAHP would complain that it does not have a value for ``foo``.
This is because ``foo`` is a required field, but neither is a value is not specified in the YAML nor is
there a default value.

Instead, ``foo`` can be set on the command line. Arugments specified in YAML can also be overridden
via the command line.

Try running ``python cli.py --foo 2 --bar 3.0``. This command should print:

.. code-block:: yaml

    SimpleExample:
        bar: 3.0
        baz: null
        foo: 2
