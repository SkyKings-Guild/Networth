import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any
from urllib.request import Request, urlopen

from .types import (
    Accessory,
    AttributeShard,
    Enchantment,
    Gemstone,
    GemstoneSlot,
    UpgradeCostUnion,
)

__all__ = (
    "ConstantsProvider",
    "DefaultConstantsProvider",
)

__all__ = (
    "ConstantsProvider",
    "DefaultConstantsProvider",
)


class ConstantsProvider(ABC):
    """Interface for loading the constants used by networth calculations."""

    @abstractmethod
    async def blocked_enchants(self) -> dict[str, list[str]]:
        """
        Get a dictionary of blocked enchantments, keyed by their ID.

        :return: A dictionary mapping enchantment IDs to lists of blocked enchantments.
        """
        ...

    @abstractmethod
    async def enchants(self) -> dict[str, Enchantment]:
        """
        Get a dictionary of all available enchantments, keyed by their ID.

        :return: A dictionary mapping enchantment IDs to their corresponding Enchantment data.
        """
        ...

    @abstractmethod
    async def accessories(self) -> dict[str, Accessory]:
        """
        A dictionary of all available accessories, keyed by their ID.

        :return: A dictionary mapping accessory IDs to their corresponding Accessory data.
        """
        ...

    @abstractmethod
    async def reforges(self) -> dict[str, str]:
        """
        A dictionary of reforges to their respective item.

        :return: A dictionary mapping reforge IDs to their corresponding item IDs.
        """
        ...

    @abstractmethod
    async def gemstones(self) -> dict[str, Gemstone]:
        """
        A dictionary of all available gemstones, keyed by their ID.

        :return: A dictionary mapping gemstone IDs to their corresponding Gemstone data.
        """
        ...

    @abstractmethod
    async def attribute_shards(self) -> dict[str, AttributeShard]:
        """
        A dictionary of all available attribute shards, keyed by their ID.

        :return: A dictionary mapping attribute shard IDs to their corresponding AttributeShard data.
        """
        ...

    @abstractmethod
    async def soulbound_items(self) -> list[str]:
        """
        A list of all soulbound items.

        :return: A list of item IDs that are considered soulbound.
        """
        ...

    @abstractmethod
    async def cosmetic_items(self) -> list[str]:
        """
        A list of all cosmetic items.

        :return: A list of item IDs that are considered cosmetic.
        """
        ...

    @abstractmethod
    async def upgrade_costs(self) -> dict[str, list[UpgradeCostUnion]]:
        """
        A dictionary of all item upgrade costs, keyed by item ID.

        :return: A dictionary mapping item IDs to lists of upgrade cost data.
        """
        ...

    @abstractmethod
    async def gemstone_slots(self) -> dict[str, list[GemstoneSlot]]:
        """
        A dictionary of all gemstone slots, keyed by item ID.

        :return: A dictionary mapping item IDs to lists of gemstone slots.
        """
        ...

    @abstractmethod
    async def dungeon_items(self) -> list[str]:
        """
        A list of all dungeon items.

        :return: A list of item IDs that are considered dungeon items.
        """
        ...


class DefaultConstantsProvider(ConstantsProvider):
    """
    A default implementation of ConstantsProvider that fetches constants
    from the SkyKings-Guild Bot-Data repository and the Hypixel API.
    """

    BASE_URL = "https://raw.githubusercontent.com/SkyKings-Guild/Bot-Data/main/"
    HYPIXEL_API_URL = "https://api.hypixel.net/v2/resources/skyblock/items"

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._item_api_response: dict[str, Any] | None = None

    async def get_constants(self, path: str) -> Any:
        if path not in self._cache:
            self._cache[path] = await asyncio.to_thread(self._fetch, path)
        return self._cache[path]

    async def get_item_api_response(self) -> dict[str, Any]:
        if self._item_api_response is None:
            self._item_api_response = await asyncio.to_thread(
                self._fetch_item_api_response
            )
        return self._item_api_response

    @classmethod
    def _fetch(cls, path: str) -> Any:
        request = Request(f"{cls.BASE_URL}{path}")
        with urlopen(request) as response:
            return json.loads(response.read())

    @classmethod
    def _fetch_item_api_response(cls) -> dict[str, Any]:
        request = Request(cls.HYPIXEL_API_URL)
        with urlopen(request) as response:
            return json.loads(response.read())

    async def blocked_enchants(self):
        return await self.get_constants("skyblock/networth/blocked_enchants.json")

    async def enchants(self):
        constants = await self.get_constants("skyblock/enchants.json")
        return {
            value["id"]: value
            for value in constants.values()
            if isinstance(value, dict)
        }

    async def accessories(self):
        return await self.get_constants("skyblock/accessories.json")

    async def reforges(self):
        return await self.get_constants("skyblock/reforges.json")

    async def gemstones(self):
        gems = await self.get_constants("skyblock/gemstones.json")
        return {
            "normal": gems.keys(),
            "special": ["UNIVERSAL", "COMBAT", "OFFENSIVE", "DEFENSIVE", "MINING"],
            "ignore": ["unlocked_slots"],
        }

    async def attribute_shards(self):
        return (await self.get_constants("skyblock/attribute_shards.json"))[
            "attributes"
        ]

    async def soulbound_items(self):
        items = await self.get_item_api_response()
        return [item["id"] for item in items.values() if item.get("soulbound", False)]

    async def cosmetic_items(self):
        items = await self.get_item_api_response()
        return [
            item["id"]
            for item in items.values()
            if item.get("category").lower() == "cosmetic"
            or "furniture" in item
            or "DISC" in item["id"].upper()
            or item["id"].upper().endswith("_PERSONALITY")
        ]

    async def upgrade_costs(self):
        items = await self.get_item_api_response()
        return {item["id"]: item.get("upgrade_costs", []) for item in items.values()}

    async def gemstone_slots(self):
        items = await self.get_item_api_response()
        return {item["id"]: item.get("gemstone_slots", []) for item in items.values()}

    async def dungeon_items(self):
        items = await self.get_item_api_response()
        return [
            item["id"] for item in items.values() if item.get("gungeon_item", False)
        ]
