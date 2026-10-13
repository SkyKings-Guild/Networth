from functools import cached_property
from typing import overload, TYPE_CHECKING, cast

from .models import (
    InventoryData,
    SkyBlockProfile,
    SkyBlockProfileMember,
    MuseumItem,
    MuseumMemberData,
    NetworthItem,
    NetworthPet,
)
from .calculators import (
    ItemAbilityScroll,
    ItemArtOfPeace,
    ItemArtOfWar,
    ItemBase,
    ItemBookOfStats,
    ItemBoosters,
    ItemCollectedCoins,
    ItemDrillParts,
    ItemDyes,
    ItemEnchant,
    ItemEthermergers,
    ItemFarmingForDummies,
    ItemGems,
    ItemGemstoneChamber,
    ItemHotPotatoBooks,
    ItemJalapenoBooks,
    ItemManaDisintegrators,
    ItemPriceCalculation,
    ItemRecombobulated,
    ItemReforge,
    ItemRunes,
    ItemSkin,
    ItemTransmissionTuners,
    ItemUpgradeLevel,
    ItemWoodSingularity,
    PetBase,
    PetCandied,
    PetHeldItem,
    PetPriceCalculation,
    PetSkin,
)
from .parsers import parse_inventory
from .pricing import PriceProvider
from .utils import DEFAULT_NW_SETTINGS
from .constants import DefaultConstantsProvider, ConstantsProvider
from .types import (
    Accessory,
    AttributeShard,
    Enchantment,
    Gemstone,
    GemstoneSlot,
    NetworthSettings,
    UpgradeCostUnion,
)

__all__ = ("NetworthManager",)


class NetworthManager:
    """
    Manages the calculation of networth for a single SkyBlock profile.

    :param profile: The SkyBlock profile to calculate networth for.
    :param museum: The museum data for the profile.
    :param uuid: The UUID of the player.
    :param constants_provider: A provider for constants used in calculations.
    :param price_provider: A provider for item prices.

    :ivar profile: The SkyBlock profile being evaluated.
    :ivar museum_data: The museum data for the profile.
    :ivar uuid: The UUID of the player.
    :ivar _constants_provider: The provider for constants used in calculations.
    :ivar _price_provider: The provider for item prices.
    :ivar _is_parsed: A flag indicating whether the profile has been parsed.
        If this is False, most of these attributes will be empty or None.
    :ivar inventory_api_disabled: A flag indicating whether the inventory API is disabled.
    :ivar inv_content: The contents of the player's inventory.
    :ivar ender_chest_contents: The contents of the player's ender chest.
    :ivar inv_armor: The contents of the player's armor slots.
    :ivar loadout_armor: The contents of the player's loadout armor slots.
    :ivar talisman_bag: The contents of the player's talisman bag.
    :ivar equipment_contents: The contents of the player's equipment slots.
    :ivar loadout_equipment: The contents of the player's loadout equipment slots.
    :ivar personal_vault_api_disabled: A flag indicating whether the personal vault API is disabled
    :ivar personal_vault_contents: The contents of the player's personal vault.
    :ivar backpack_contents: The contents of the player's backpacks.
    :ivar museum_api_disabled: A flag indicating whether the museum API is disabled.
    :ivar museum_contents: The contents of the player's museum.
    :ivar sacks: The counts of the player's sacks.
    :ivar sacks_value: The total value of the player's sacks.
    :ivar essences: The counts of the player's essences.
    :ivar essences_value: The total value of the player's essences.
    :ivar hunting_box: The counts of the player's hunting box shards.
    :ivar hunting_box_value: The total value of the player's hunting box shards.
    :ivar attributes: The counts of the player's attribute shards.
    :ivar attributes_value: The total value of the player's attribute shards.
    :ivar coop_bank: The amount of coins in the player's coop bank.
    :ivar personal_bank: The amount of coins in the player's personal bank.
    :ivar purse: The amount of coins in the player's purse.
    :ivar pets: The list of the player's pets.
    """
    ITEM_CALCULATORS: tuple[type[ItemPriceCalculation], ...] = (
        ItemBase,
        ItemEnchant,
        ItemRecombobulated,
        ItemGems,
        ItemReforge,
        ItemSkin,
        ItemDyes,
        ItemRunes,
        ItemUpgradeLevel,
        ItemAbilityScroll,
        ItemGemstoneChamber,
        ItemArtOfPeace,
        ItemArtOfWar,
        ItemHotPotatoBooks,
        ItemFarmingForDummies,
        ItemJalapenoBooks,
        ItemWoodSingularity,
        ItemTransmissionTuners,
        ItemManaDisintegrators,
        ItemEthermergers,
        ItemBoosters,
        ItemCollectedCoins,
        ItemDrillParts,
        ItemBookOfStats,
    )

    PET_CALCULATORS: tuple[type[PetPriceCalculation], ...] = (
        PetBase,
        PetCandied,
        PetHeldItem,
        PetSkin,
    )

    def __init__(
        self,
        profile: SkyBlockProfile | None,
        museum: MuseumMemberData | None,
        uuid: str,
        *,
        constants_provider: ConstantsProvider | None = None,
        price_provider: PriceProvider,
    ) -> None:
        self.profile: SkyBlockProfile | None = profile
        self.museum_data: MuseumMemberData | None = museum
        self.uuid: str = uuid
        self._constants_provider = constants_provider or DefaultConstantsProvider()
        self._price_provider = price_provider
        # Parsing stuff
        self._is_parsed: bool = False
        self.inventory_api_disabled: bool = False
        self.inv_content: list[NetworthItem] = []
        self.ender_chest_contents: list[NetworthItem] = []
        self.inv_armor: list[NetworthItem] = []
        self.loadout_armor: list[NetworthItem] = []
        self.talisman_bag: list[NetworthItem] = []
        self.equipment_contents: list[NetworthItem] = []
        self.loadout_equipment: list[NetworthItem] = []
        self.personal_vault_api_disabled: bool = False
        self.personal_vault_contents: list[NetworthItem] = []
        self.backpack_contents: list[NetworthItem] = []
        self.museum_api_disabled: bool = museum is None
        self.museum_contents: list[NetworthItem] = []
        self.sacks: dict[str, int] | None = None
        self.sacks_value: dict[str, int] | None = None
        self.essences: dict[str, int] | None = None
        self.essences_value: dict[str, int] | None = None
        self.hunting_box: dict[str, int] | None = None
        self.hunting_box_value: dict[str, int] | None = None
        self.attributes: dict[str, int] | None = None
        self.attributes_value: dict[str, int] | None = None
        self.coop_bank: int | None = None
        self.personal_bank: int | None = None
        self.purse: int = 0
        self.pets: list[NetworthPet] = []
        # Evaluation data
        self._price_data: dict[str, int] | None = None
        self._upgrade_costs = None
        self._gemstone_slots = None
        self._dungeon_items = None
        self._soulbound_items: set[str] | None = None
        self._cosmetic_items: set[str] | None = None

    @property
    def total_sacks_value(self) -> int:
        """Returns the total value of all sacks in the profile."""
        if self.sacks_value is None:
            return 0
        return sum(self.sacks_value.values())

    @property
    def total_essences_value(self) -> int:
        """Returns the total value of all essences in the profile."""
        if self.essences_value is None:
            return 0
        return sum(self.essences_value.values())

    @property
    def total_hunting_box_value(self) -> int:
        """Returns the total value of all hunting box shards in the profile."""
        if self.hunting_box_value is None:
            return 0
        return sum(self.hunting_box_value.values())

    @property
    def total_attributes_value(self) -> int:
        """Returns the total value of all attribute shards in the profile."""
        if self.attributes_value is None:
            return 0
        return sum(self.attributes_value.values())

    @classmethod
    async def evaluate_single_item(
        cls,
        item: NetworthItem,
        *,
        constants_provider: ConstantsProvider | None = None,
        price_provider: PriceProvider,
    ) -> NetworthItem:
        """
        Evaluates a single item for its networth value.

        :param item: The item to evaluate.
        :param constants_provider: A provider for constants used in calculations.
        :param price_provider: A provider for item prices.
        :return: The evaluated item with its networth value calculated.
        """
        settings: NetworthSettings = set(DEFAULT_NW_SETTINGS)
        manager = cls(
            None,
            None,
            "",
            constants_provider=constants_provider,
            price_provider=price_provider,
        )
        item.reset()
        if await item.should_evaluate(manager, settings):
            for calculator in manager.ITEM_CALCULATORS:
                await calculator.calculate(manager, item, settings=settings)
        del manager
        return item

    async def parse(self):
        """
        Parses the profile data and populates the inventory, museum, and other relevant data internally.
        """
        assert self.profile is not None
        if self._is_parsed:
            raise RuntimeError("NetworthManager has already been parsed.")
        self._is_parsed = True
        member = self.member_data
        assert member is not None
        inventory = member.inventory
        if inventory is None or inventory.inv_contents is None:
            self.inventory_api_disabled = True
            return
        self.inv_content = await parse_inventory(inventory.inv_contents.data)
        self.ender_chest_contents = (
            await parse_inventory(inventory.ender_chest_contents.data)
            if inventory.ender_chest_contents
            else []
        )
        self.inv_armor = (
            await parse_inventory(inventory.inv_armor.data)
            if inventory.inv_armor
            else []
        )
        self.loadout_armor = []
        if member.loadout:
            armor_data = member.loadout.armor
            if armor_data is not None:
                equipped_slot = armor_data.get("equipped_set", None)
                if equipped_slot is not None:
                    armor_data.pop(str(equipped_slot), None)
                    armor_data.pop("equipped_set", None)
                armor_data = cast(dict[str, dict[str, InventoryData]], armor_data)
                for slot_data in armor_data.values():
                    slot_data.pop("id", None)
                    for piece in slot_data.values():
                        self.loadout_armor += await parse_inventory(piece.data)
        self.talisman_bag = (
            await parse_inventory(inventory.bag_contents.talisman_bag.data)
            if inventory.bag_contents and inventory.bag_contents.talisman_bag
            else []
        )
        self.equipment_contents = (
            await parse_inventory(inventory.equipment_contents.data)
            if inventory.equipment_contents
            else []
        )
        self.loadout_equipment = []
        if member.loadout:
            equipment_data = member.loadout.equipment
            if equipment_data is not None:
                equipped_slot = equipment_data.get("equipped_set", None)
                if equipped_slot is not None:
                    equipment_data.pop(str(equipped_slot), None)
                    equipment_data.pop("equipped_set", None)
                equipment_data = cast(
                    dict[str, dict[str, InventoryData]], equipment_data
                )
                for slot_data in equipment_data.values():
                    slot_data.pop("id", None)
                    for piece in slot_data.values():
                        self.loadout_equipment += await parse_inventory(piece.data)
        if inventory.personal_vault_contents is None:
            self.personal_vault_api_disabled = True
        else:
            self.personal_vault_contents = await parse_inventory(
                inventory.personal_vault_contents.data
            )
        if inventory.backpack_contents is not None:
            for backpack in inventory.backpack_contents.values():
                self.backpack_contents.extend(await parse_inventory(backpack.data))
        if not self.museum_api_disabled and self.museum_data is not None:
            items_to_parse: list[MuseumItem] = (
                list(self.museum_data.items.values()) + self.museum_data.special
            )
            for item in items_to_parse:
                if item.borrowing:
                    continue
                if not item.items:
                    continue
                self.museum_contents.extend(await parse_inventory(item.items.data))
        self.sacks = inventory.sacks_counts
        if member.shards and member.shards.owned:
            self.hunting_box = {
                shard.type: shard.amount_owned for shard in member.shards.owned
            }
        else:
            self.hunting_box = {}
        if member.attributes and member.attributes.stacks:
            self.attributes = member.attributes.stacks
        else:
            self.attributes = {}
        if member.currencies:
            self.essences = {k: v.current for k, v in member.currencies.essence.items()}
            self.purse = int(member.currencies.coin_purse)
        if self.profile.banking is not None:
            self.coop_bank = int(self.profile.banking.balance)
        else:
            self.coop_bank = None
        if member.profile.bank_account:
            self.personal_bank = int(member.profile.bank_account)
        else:
            self.personal_bank = None

        self.pets = (
            [NetworthPet(**pet.model_dump()) for pet in member.pets_data.pets]
            if member.pets_data
            else []
        )

    async def evaluate(self, settings: NetworthSettings):
        """
        Evaluates the networth of the profile based on the provided settings.

        :param settings: The settings to use for evaluation, determining which items and features to include in the networth calculation.
        :type settings: NetworthSettings
        """
        if not self._is_parsed:
            await self.parse()
        for item in self.all_items:
            item.reset()
            if await item.should_evaluate(self, settings):
                for calculator in self.ITEM_CALCULATORS:
                    await calculator.calculate(self, item, settings=settings)
        for pet in self.pets:
            pet.reset()
            if await pet.should_evaluate(self, settings):
                for calculator in self.PET_CALCULATORS:
                    await calculator.calculate(self, pet, settings=settings)

        # sacks
        self.sacks_value = {}
        if self.sacks:
            for item, count in self.sacks.items():
                key = item.lower()
                if value := await self.get_price(key):
                    self.sacks_value[key] = value * count

        # essences
        self.essences_value = {}
        if self.essences:
            for essence, count in self.essences.items():
                key = f"essence_{essence}".lower()
                if value := await self.get_price(key):
                    self.essences_value[key] = value * count

        # hunting_box
        self.hunting_box_value = {}
        if self.hunting_box and "hunting box" in settings:
            for shard, count in self.hunting_box.items():
                key = ("SHARD_" + shard).lower()
                if value := await self.get_price(key):
                    self.hunting_box_value[shard] = value * count

        # attributes
        self.attributes_value = {}
        attr_data = await self.attribute_shards()
        if self.attributes and "attributes" in settings:
            for attribute, count in self.attributes.items():
                if attribute not in attr_data:
                    continue
                key = attr_data[attribute]["bazaar_id"].lower()
                if value := await self.get_price(key):
                    self.attributes_value[attribute] = value * count

    # Data fetchers
    async def blocked_enchants(self) -> dict[str, list[str]]:
        """
        Fetches the blocked enchantments from the constants provider.
        :return: A dictionary mapping enchantment IDs to lists of blocked enchantments.
        """
        return await self._constants_provider.blocked_enchants()

    async def enchants(self) -> dict[str, Enchantment]:
        """
        Fetches the enchantments from the constants provider.
        :return: A dictionary mapping enchantment IDs to their corresponding Enchantment data.
        """
        return await self._constants_provider.enchants()

    async def accessories(self) -> dict[str, Accessory]:
        """
        Fetches the accessories from the constants provider.
        :return: A dictionary mapping accessory IDs to their corresponding Accessory data.
        """
        return await self._constants_provider.accessories()

    async def reforges(self) -> dict[str, str]:
        """
        Fetches the reforges from the constants provider.
        :return: A dictionary mapping reforge IDs to their corresponding item IDs.
        """
        return await self._constants_provider.reforges()

    async def gemstones(self) -> dict[str, Gemstone]:
        """
        Fetches the gemstones from the constants provider.
        :return: A dictionary mapping gemstone IDs to their corresponding Gemstone data.
        """
        return await self._constants_provider.gemstones()

    async def attribute_shards(self) -> dict[str, AttributeShard]:
        """
        Fetches the attribute shards from the constants provider.
        :return: A dictionary mapping attribute shard IDs to their corresponding AttributeShard data.
        """
        return await self._constants_provider.attribute_shards()

    async def soulbound_items(self) -> list[str]:
        """
        Fetches the soulbound items from the constants provider.
        :return: A list of item IDs that are considered soulbound.
        """
        return await self._constants_provider.soulbound_items()

    async def cosmetic_items(self) -> list[str]:
        """
        Fetches the cosmetic items from the constants provider.
        :return: A list of item IDs that are considered cosmetic.
        """
        return await self._constants_provider.cosmetic_items()

    async def upgrade_costs(self) -> dict[str, list[UpgradeCostUnion]]:
        """
        Fetches the upgrade costs from the constants provider.
        :return: A dictionary mapping item IDs to lists of upgrade cost data.
        """
        return await self._constants_provider.upgrade_costs()

    async def gemstone_slots(self) -> dict[str, list[GemstoneSlot]]:
        """
        Fetches the gemstone slots from the constants provider.
        :return: A dictionary mapping item IDs to lists of gemstone slots.
        """
        return await self._constants_provider.gemstone_slots()

    async def dungeon_items(self) -> list[str]:
        """
        Fetches the dungeon items from the constants provider.
        :return: A list of item IDs that are considered dungeon items.
        """
        return await self._constants_provider.dungeon_items()

    @overload
    async def get_price(self, item_id: str) -> int: ...

    @overload
    async def get_price(self, item_id: str, default: int) -> int: ...

    @overload
    async def get_price(self, item_id: str, default: None) -> int | None: ...

    async def get_price(self, item_id: str, default: int | None = 0) -> int | None:
        """
        Fetches the price of an item using the price provider.
        :param item_id: The ID of the item to fetch the price for.
        :param default: The default value to return if the price is not found. Defaults to 0.
        :return: The price of the item, or the default value if not found.
        """
        return await self._price_provider.get_price(item_id, default=default)

    @property
    def all_items(self) -> list[NetworthItem]:
        """
        Returns a list of all items in all inventories in the profile.
        :return: A list of all NetworthItem objects in the profile's inventories.
        """
        if not self._is_parsed:
            raise RuntimeError("NetworthManager has not been parsed yet.")
        return (
            self.inv_content
            + self.ender_chest_contents
            + self.inv_armor
            + self.loadout_armor
            + self.talisman_bag
            + self.equipment_contents
            + self.loadout_equipment
            + self.personal_vault_contents
            + self.backpack_contents
            + self.museum_contents
        )

    @cached_property
    def member_data(self) -> SkyBlockProfileMember | None:
        """
        Returns the member data for the player with the given UUID.
        :return: The SkyBlockProfileMember object for the player, or None if not found.
        """
        if self.profile is None:
            return None
        return self.profile.members.get(self.uuid, None)

    def set_museum_data(self, museum: MuseumMemberData | None) -> None:
        """
        Sets the museum data for the profile and updates the museum API disabled flag.
        :param museum: The MuseumMemberData object to set for the profile, or None if the museum API is disabled.
        """
        self.museum_data = museum
        self.museum_api_disabled = museum is None

    @property
    def total_networth(self) -> int:
        """
        Calculates the total networth of the profile by summing the values of all items, pets, sacks, essences, hunting box shards,
        attribute shards, coop bank, personal bank, and purse.
        :return: The total networth value as an integer.
        """
        return (
            sum(item.value for item in self.all_items)
            + sum(pet.value for pet in self.pets)
            + self.total_sacks_value
            + self.total_essences_value
            + self.total_hunting_box_value
            + self.total_attributes_value
            + (self.coop_bank or 0)
            + (self.personal_bank or 0)
            + self.purse
        )
