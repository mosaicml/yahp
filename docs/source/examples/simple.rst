Simple
======

YAHP can load a YAML file and parse it into the dataclass.

Consider the following YAML called ``simple.yaml``:

.. literalinclude:: ../../../examples/simple/simple.yaml


Now, consider the following script that defines the
:class:`~yahp.hparams.Hparams` and loads this YAML file:

.. literalinclude:: ../../../examples/simple/simple.py
    :linenos:


This script will output:

.. code-block:: yaml

    SimpleExample:
        bar: 3.0
        baz: null
        foo: 2
