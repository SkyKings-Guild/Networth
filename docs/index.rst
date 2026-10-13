.. SkyNetworth documentation master file, created by
   sphinx-quickstart on Mon Oct 12 00:59:37 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

SkyNetworth
============
A package to calculate a SkyBlock player's networth.


.. toctree::
   :maxdepth: 1

   api/calculators
   api/constants
   api/manager
   api/parsers
   api/pricing
   api/types
   api/utils
   api/models


Installation
-------------

You can install the package via pip:

.. code-block:: bash

   pip install skynetworth

Usage
------

Calculating a player's networth is based around the ``NetworthManager`` class.
``NetworthManager`` takes in 5 parameters:

* The player's profile data.
* The player's museum data.
* The player's UUID.
* A constant provider.
* A price provider.

.. code-block:: python3

   import skynetworth

   # Create a new NetworthManager instance
   manager = skynetworth.NetworthManager(
       profile=profile,
       museum=museum,
       uuid=uuid,
       constant_provider=skynetworth.DefaultConstantsProvider(),
       price_provider=skynetworth.DictPriceProvider(prices),
   )

   manager.evaluate(skynetworth.DEFAULT_NW_SETTINGS)
   print(manager.total_networth)

   # Non-cosmetic
   # You do not need to recreate the NetworthManager instance to evaluate different settings.
   # You can simply call the `evaluate` method with a new set of settings.
   manager.evaluate({"museum", "hunting_box", "attributes"})
   print(manager.total_networth)

Pricing Information
~~~~~~~~~~~~~~~~~~~~

The package does not provide any pricing information. You will need to provide your own pricing information via a price provider. The package comes with a `DictPriceProvider` class that takes in a dictionary of prices.

.. code-block:: python3

   prices = {
       "item_id": 1000,
       "another_item_id": 500,
   }

   skynetworth.DictPriceProvider(prices)

You can also create your own price provider by implementing the ``PriceProvider`` ABC.

There are a few things worth noting when creating your prices:

- All price keys are expected to be lowercase.
- **Pets**: Pet prices are requested using the key ``lvl_<level>_<tier>_<type>`` (i.e. ``lvl_200_legendary_golden_dragon``).
- **Enchantments**: Enchantment prices are requested using the key ``enchant_<enchantment_name>_<level>`` (i.e. ``enchant_protection_5``).
- **All Other Items**: All other items are requested using the item's ID as found in the player inventory, or in the Hypixel API.

Issues
-------

If you encounter any issues or have feature requests,
please open an issue in the `GitHub repository <https://github.com/SkyKings-Guild/networth/issues>`_
or open a ticket on the `SkyKings Discord <https://discord.gg/skyblock>`_.

Contributing
-------------

Contributions are welcome! We use ``uv`` for development. To get started, clone the repository and set up your environment:

.. code-block:: python3

   uv sync

License
--------

This project is licensed under the BSD 3-Clause License. See the `LICENSE <LICENSE.md>`_ file for details.
