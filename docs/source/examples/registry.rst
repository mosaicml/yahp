.. _Registry Example:

Registry
========



YAHP also supports instantiating concrete sub-classes of abstract fields
directly from the YAML or the command line.

Singleton Example
#################

Consider the following script that defines the
:class:`~yahp.hparams.Hparams`:

.. literalinclude:: ../../../examples/registry/registry.py
    :linenos:
    :end-before: [foo_hparams]

Suppose ``registry_foo.yaml`` contains the following:

.. literalinclude:: ../../../examples/registry/registry_foo.yaml

Then, the following example will load ``owner`` to the child.

.. literalinclude:: ../../../examples/registry/registry.py
    :linenos:
    :start-after: [foo_hparams]
    :end-before: [bar_dataclass]

It will print the following:

.. code-block:: yaml

    FooHparams:
        owner:
            child:
                name: Bob
                parents:
                - Alice
                - Charlie


List Example
############
Suppose we wanted to permit multiple owners.
Consider the following :class:`~yahp.hparams.Hparams`:

.. literalinclude:: ../../../examples/registry/registry.py
    :linenos:
    :start-after: [bar_dataclass]
    :end-before: [bar_hparams]

Suppose ``registry_bar.yaml`` contains the following:

.. literalinclude:: ../../../examples/registry/registry_bar.yaml

Then, the following example will load ``owners`` to the adult and the child.

.. literalinclude:: ../../../examples/registry/registry.py
    :linenos:
    :start-after: [bar_hparams]

It will print the following:

.. code-block:: yaml

    BarHparams:
        owners:
        - adult:
            name: Alice
            num_children: 1
        - child:
            name: Bob
            parents:
            - Alice
            - Charlie
