from abc import ABC, abstractmethod
from typing import Any, overload, TypeVar


__all__ = (
    "PriceProvider",
    "DictPriceProvider",
)


class PriceProvider(ABC):
    """
    Interface for loading the prices of items used by networth calculations.

    - All price keys are expected to be lowercase.
    - **Pets**: Pet prices are requested using the key `lvl_<level>_<tier>_<type>` (i.e. `lvl_200_legendary_golden_dragon`).
    - **Enchantments**: Enchantment prices are requested using the key `enchant_<enchantment_name>_<level>` (i.e. `enchant_protection_5`).
    - **All Other Items**: All other items are requested using the item's ID as found in the player inventory, or in the Hypixel API.
    """
    @overload
    async def get_price(self, item_id: str) -> int: ...

    @overload
    async def get_price(self, item_id: str, default: int) -> int: ...

    @overload
    async def get_price(self, item_id: str, default: None) -> int | None: ...

    @abstractmethod
    async def get_price(self, item_id: str, default: int | None = 0) -> int | None:
        """
        Get the price of an item by its ID.
        :param item_id: The ID of the item for which to get the price.
        :param default: The default value to return if the item is not found.
        :return: The price of the item, or the default value if the item is not found.
        """
        ...


class DictPriceProvider(PriceProvider):
    """
    A simple implementation of PriceProvider that uses a dictionary to store item prices.

    - All price keys are expected to be lowercase.
    - **Pets**: Pet prices are requested using the key `lvl_<level>_<tier>_<type>` (i.e. `lvl_200_legendary_golden_dragon`).
    - **Enchantments**: Enchantment prices are requested using the key `enchant_<enchantment_name>_<level>` (i.e. `enchant_protection_5`).
    - **All Other Items**: All other items are requested using the item's ID as found in the player inventory, or in the Hypixel API.

    :param prices: A dictionary mapping item IDs to their prices. Keys should be lowercase.
    """
    def __init__(self, prices: dict[str, int]):
        self.prices = {k.lower(): v for k, v in prices.items()}

    @overload
    async def get_price(self, item_id: str) -> int: ...

    @overload
    async def get_price(self, item_id: str, default: int) -> int: ...

    @overload
    async def get_price(self, item_id: str, default: None) -> int | None: ...

    async def get_price(self, item_id: str, default: int | None = 0) -> int | None:
        return self.prices.get(item_id.lower(), default)
