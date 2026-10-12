import asyncio
from typing import TYPE_CHECKING, cast

import warnings
from pydantic import Field, BaseModel as Model

from .utils import remove_minecraft_formatting, pet_skill_level, to_roman_numerals
from .types import EssenceUpgradeCost, NetworthSettings, UpgradeCostUnion

if TYPE_CHECKING:
    from .models import (
        Pet,
        ItemGem,
        NetworthItem,
        NetworthPet,
        ParsedGemstone,
    )
    from .manager import NetworthManager

__all__ = (
    "PriceCalculation",
    "ItemPriceCalculation",
    "ItemBase",
    "ItemEnchant",
    "ItemRecombobulated",
    "ItemGems",
    "ItemReforge",
    "ItemSkin",
    "ItemDyes",
    "ItemRunes",
    "ItemUpgradeLevel",
    "ItemAbilityScroll",
    "ItemGemstoneChamber",
    "ItemArtOfPeace",
    "ItemArtOfWar",
    "ItemHotPotatoBooks",
    "ItemFarmingForDummies",
    "ItemJalapenoBooks",
    "ItemWoodSingularity",
    "ItemTransmissionTuners",
    "ItemManaDisintegrators",
    "ItemEthermergers",
    "ItemBoosters",
    "ItemCollectedCoins",
    "ItemDrillParts",
    "ItemBookOfStats",
    "ItemCakeBagCakes",
    "PetPriceCalculation",
    "PetBase",
    "PetCandied",
    "PetHeldItem",
    "PetSkin",
)


async def parse_item_gems(
    gems: "dict[str, str | list[str] | ItemGem]", *, slots
) -> list["ParsedGemstone"]:
    from .models import ParsedGemstone, ItemGem

    parsed = []

    for key, value in gems.items():
        if key in slots["ignore"]:
            continue
        if key.endswith("_gem"):
            continue

        slot_type = key.split("_")[0]
        if isinstance(value, ItemGem):
            value = value.quality

        if slot_type in slots["normal"]:
            parsed.append(ParsedGemstone(type=slot_type, tier=cast(str, value)))
        elif slot_type in slots["special"]:
            parsed.append(
                ParsedGemstone(
                    type=cast(str, gems[key + "_gem"]), tier=cast(str, value)
                )
            )
        else:
            parsed.append(ParsedGemstone(type=key, tier=cast(str, value)))
    return parsed


async def get_pet_prices_from_db(
    pet: "Pet", manager: "NetworthManager"
) -> tuple[float | None, float | None, float | None]:
    lvl1 = await manager.get_price(f"lvl_1_{pet.tier}_{pet.type}".lower(), None)
    lvl100 = await manager.get_price(f"lvl_100_{pet.tier}_{pet.type}".lower(), None)
    lvl200 = await manager.get_price(f"lvl_200_{pet.tier}_{pet.type}".lower(), None)
    return lvl1, lvl100, lvl200


class PriceCalculation(Model):
    id: str
    display: str
    value: int
    debug_info: dict = Field(default_factory=dict)


# Items
class ItemPriceCalculation(PriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None: ...


class ItemBase(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        base_id = item.item_id.lower()
        if base_id == "enchanted_book":
            return None
        value = await manager.get_price(base_id, 0)
        if value == 0:
            # shen?
            if item.attributes and item.attributes.price is not None:
                item.calculations.append(
                    cls(
                        id=f"shen:{base_id}",
                        display=remove_minecraft_formatting(item.item_name)
                        + " (Price paid at auction)",
                        value=item.attributes.price,
                    )
                )
                return None
        item.calculations.append(
            cls(
                id=f"base:{base_id}",
                display=remove_minecraft_formatting(item.item_name),
                value=value,
            )
        )
        return None


class ItemEnchant(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        blocked_enchants = await manager.blocked_enchants()
        enchants = await manager.enchants()

        if item.attributes is None or item.attributes.enchantments is None:
            return None

        for enchant, level in item.attributes.enchantments.items():
            enchant = enchant.lower()
            enchant_info = enchants.get(enchant)
            if enchant_info is None:
                item.calculations.append(
                    cls(
                        id=f"enchant:{enchant}",
                        display=enchant,
                        value=0,
                        debug_info={
                            "enchant": enchant,
                            "level": level,
                            "details": "unknown enchant",
                        },
                    )
                )
                continue
            enchant_name = f"{enchant_info['name']} {to_roman_numerals(level)}"
            enchant_id = f"enchantment_{enchant}_{level}"
            if enchant in blocked_enchants.get(item.item_id, []):
                item.calculations.append(
                    cls(
                        id=enchant_id,
                        display=enchant_name,
                        value=0,
                        debug_info={
                            "enchant": enchant,
                            "level": level,
                            "details": "blocked enchant",
                        },
                    )
                )
                continue
            if enchant_info["max_table"] >= level:
                item.calculations.append(
                    cls(
                        id=enchant_id,
                        display=enchant_name,
                        value=0,
                        debug_info={
                            "enchant": enchant,
                            "level": level,
                            "details": "enchantment table",
                        },
                    )
                )
                continue

            # determine enchantment value
            if enchant_info.get("stacking", False):
                value = await manager.get_price(f"enchantment_{enchant}_1", 0)
                item.calculations.append(
                    cls(
                        id=enchant_id,
                        display=enchant_name,
                        value=value,
                        debug_info={
                            "enchant": enchant,
                            "level": level,
                            "details": "stacking enchant",
                        },
                    )
                )
                continue
            # upgrade stones
            value = 0
            debug_info = {}
            is_stonk = item.item_id.upper() == "STONK_PICKAXE"
            start_e_level = level
            while (
                stone := enchant_info.get("upgrade_stones", {}).get(str(level))
            ) is not None:
                stone_price = await manager.get_price(stone.lower(), 0)
                value += stone_price
                debug_info[f"level {level} upgrade stone {stone}"] = stone_price
                level -= 1
                if is_stonk and level <= 6:
                    break
            if not is_stonk:
                buy_price = await manager.get_price(f"enchantment_{enchant}_{level}", 0)
                debug_info["buy price"] = buy_price
                if enchant_info["max_table"] == 0:
                    crafting_price = await manager.get_price(
                        f"enchantment_{enchant}_1", 0
                    )
                    debug_info["* level 1"] = crafting_price
                    # combine 2 to make +1 level, do this until we hit level
                    crafting_price = crafting_price * (2 ** (level - 1))
                    debug_info["crafting price"] = crafting_price
                    if buy_price == 0:
                        value += crafting_price
                    elif crafting_price == 0:
                        value += buy_price
                    else:
                        value += min(buy_price, crafting_price)
                else:
                    value += buy_price
            item.calculations.append(
                cls(
                    id=enchant_id,
                    display=enchant_name,
                    value=value,
                    debug_info={
                        "enchant": enchant,
                        "level": start_e_level,
                        **debug_info,
                    },
                )
            )

        return None


class ItemRecombobulated(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or not item.recombobulated:
            return None
        if item.item_id.lower() in await manager.accessories():
            return None
        value = await manager.get_price("recombobulator_3000", 0)
        item.calculations.append(
            cls(
                id="recombobulator_3000",
                display="Recombobulator 3000",
                value=value,
            )
        )
        return None


class ItemGems(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.gems is None:
            return None
        parsed_gems = await parse_item_gems(
            item.attributes.gems, slots=await manager.gemstones()
        )
        for gem in parsed_gems:
            gem_id = f"{gem.tier.lower()}_{gem.type.lower()}_gem"
            gem_name = f"{gem.tier.title()} {gem.type.title()} Gem"
            value = await manager.get_price(gem_id.lower(), 0)
            item.calculations.append(
                cls(
                    id=gem_id,
                    display=gem_name,
                    value=value,
                    debug_info={"type": gem.type, "tier": gem.tier},
                )
            )
        # slot unlocks
        if item.attributes.gems.get("unlocked_slots", None):
            slot_data = (await manager.gemstone_slots()).get(item.item_id.upper(), None)
            if slot_data is not None:
                for slot in item.attributes.gems["unlocked_slots"]:
                    if not isinstance(slot, str):
                        # should always be a string here
                        warnings.warn("Expected string for gemstone slot")
                        continue
                    slot_type, slot_num = slot.split("_")
                    slot_value = 0
                    slot_index = 0
                    for slot_info in slot_data:
                        if slot_info["slot_type"] == slot_type:
                            if slot_index == int(slot_num):
                                if "costs" not in slot_info:
                                    break
                                debug_costs = {}
                                for cost in slot_info["costs"]:
                                    if cost["type"] == "COINS":
                                        slot_value += cost["coins"]
                                    elif cost["type"] == "ITEM":
                                        p = await manager.get_price(
                                            cost["item_id"].lower(), 0
                                        )
                                        debug_costs[f"item_{cost['item_id']}"] = p
                                        slot_value += p * cost["amount"]
                                item.calculations.append(
                                    cls(
                                        id=f"gemstone_slot_{slot_type}_{slot_num}",
                                        display=f"Unlock {slot_type.title()} Gemstone Slot {int(slot_num) + 1}",
                                        value=slot_value,
                                        debug_info={
                                            "slot_type": slot_type,
                                            "slot_num": slot_num,
                                            "costs": slot_info["costs"],
                                            "items": debug_costs,
                                        },
                                    )
                                )
                                break
                            else:
                                slot_index += 1
        return None


class ItemReforge(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.modifier is None:
            return None
        reforges = await manager.reforges()
        reforge_item = reforges.get(item.attributes.modifier.lower())
        if reforge_item is None:
            item.calculations.append(
                cls(
                    id=f"reforge:{item.attributes.modifier}",
                    display="Reforge Item",
                    value=0,
                    debug_info={
                        "reforge": item.attributes.modifier,
                        "details": "no item found",
                    },
                )
            )
            return None
        value = await manager.get_price(reforge_item.lower(), 0)
        item.calculations.append(
            cls(
                id=f"reforge:{item.attributes.modifier}",
                display="Reforge",
                value=value,
                debug_info={"reforge": item.attributes.modifier, "item": reforge_item},
            )
        )
        return None


class ItemSkin(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.skin is None:
            return None
        if settings is not None and "cosmetic mods" not in settings:
            return None
        value = await manager.get_price(item.attributes.skin.lower(), 0)
        item.calculations.append(
            cls(
                id=item.attributes.skin,
                display="Skin",
                value=value,
                debug_info={"skin": item.attributes.skin},
            )
        )
        return None


class ItemDyes(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.dye is None:
            return None
        if settings is not None and "cosmetic mods" not in settings:
            return None
        value = await manager.get_price(item.attributes.dye.lower(), 0)
        item.calculations.append(
            cls(
                id=item.attributes.dye,
                display="Dye",
                value=value,
                debug_info={"dye": item.attributes.dye},
            )
        )
        return None


class ItemRunes(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or not item.attributes.runes:
            return None
        if settings is not None and "cosmetic mods" not in settings:
            return None
        calc = cls(
            id="runes",
            display="Runes",
            value=0,
            debug_info={"runes": []},
        )
        for rune, lvl in item.attributes.runes.items():
            rune_id = f"{rune}_{lvl}_rune".lower()
            price = await manager.get_price(rune_id, 0)
            calc.value += price
            calc.debug_info["runes"].append({"id": rune_id, "price": price})
        item.calculations.append(calc)
        return None


class ItemUpgradeLevel(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.upgrade_level <= 0:
            return None
        upgrade_level = item.attributes.upgrade_level
        costs: list[UpgradeCostUnion] = (await manager.upgrade_costs()).get(
            item.item_id.upper(), []
        )
        calc = cls(
            id="upgrade_level",
            display="Stars",
            value=0,
            debug_info={},
        )
        for level in range(upgrade_level):
            if level >= len(costs):
                break
            for i, cost in enumerate(costs[level]):
                cost: UpgradeCostUnion = cast(UpgradeCostUnion, cost)
                if cost["type"] == "ESSENCE":
                    p = await manager.get_price(
                        f"essence_{cost['essence_type'].lower()}", 0
                    )
                    calc.value += p * cost["amount"]
                    calc.debug_info[f"upgrade {level} cost {i}"] = {
                        **cost,
                        "price_per": p,
                    }
                elif cost["type"] == "ITEM":
                    p = await manager.get_price(cost["item_id"].lower(), 0)
                    calc.value += p * cost["amount"]
                    calc.debug_info[f"upgrade {level} cost {i}"] = {
                        **cost,
                        "price_per": p,
                    }
                else:
                    calc.debug_info[f"upgrade {level} cost {i}"] = {
                        **cost,
                        "unknown": True,
                    }

        if (
            item.attributes.upgrade_level > 5
            and item.item_id.upper() in await manager.dungeon_items()
        ):
            master_stars = upgrade_level - 5
            for star in range(min(master_stars, 5)):
                star_name = [
                    "first_master_star",
                    "second_master_star",
                    "third_master_star",
                    "fourth_master_star",
                    "fifth_master_star",
                ][star]
                price = await manager.get_price(star_name, 0)
                calc.value += price
                calc.debug_info[f"master star {star + 1}"] = price
        item.calculations.append(calc)
        return None


class ItemAbilityScroll(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or (
            not item.attributes.ability_scrolls
            and not item.attributes.power_ability_scroll
        ):
            return None
        calc = cls(
            id="ability_scrolls",
            display="Ability Scrolls",
            value=0,
            debug_info={"scrolls": []},
        )
        for scroll in item.attributes.ability_scrolls:
            price = await manager.get_price(scroll.lower(), 0)
            calc.value += price
            calc.debug_info["scrolls"].append({"id": scroll, "price": price})
        if item.attributes.power_ability_scroll:
            price = await manager.get_price(
                item.attributes.power_ability_scroll.lower(), 0
            )
            calc.value += price
            calc.debug_info["scrolls"].append(
                {
                    "id": item.attributes.power_ability_scroll,
                    "price": price,
                    "power": True,
                }
            )
        item.calculations.append(calc)
        return None


class ItemGemstoneChamber(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.gemstone_slots <= 0:
            return None
        price = await manager.get_price("gemstone_chamber", 0)
        item.calculations.append(
            cls(
                id="gemstone_chamber",
                display="Gemstone Chamber",
                value=price * item.attributes.gemstone_slots,
                debug_info={
                    "slots": item.attributes.gemstone_slots,
                    "price_per": price,
                },
            )
        )
        return None


class ItemArtOfPeace(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or not item.attributes.art_of_peace_applied:
            return None
        value = await manager.get_price("the_art_of_peace", 0)
        item.calculations.append(
            cls(
                id="the_art_of_peace",
                display="Art of Peace",
                value=value,
            )
        )
        return None


class ItemArtOfWar(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.art_of_war_count <= 0:
            return None
        value = await manager.get_price("the_art_of_war", 0)
        item.calculations.append(
            cls(
                id="the_art_of_war",
                display="Art of War",
                value=value * item.attributes.art_of_war_count,
                debug_info={
                    "count": item.attributes.art_of_war_count,
                    "price_per": value,
                },
            )
        )
        return None


class ItemHotPotatoBooks(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.hot_potato_count <= 0:
            return None
        hpb_count = min(item.attributes.hot_potato_count, 10)
        price = await manager.get_price("hot_potato_book", 0)
        item.calculations.append(
            cls(
                id="hot_potato_book",
                display="Hot Potato Books",
                value=price * hpb_count,
                debug_info={"count": hpb_count, "price_per": price},
            )
        )
        if item.attributes.hot_potato_count > 10:
            fpb_count = item.attributes.hot_potato_count - 10
            f_price = await manager.get_price("fuming_potato_book", 0)
            item.calculations.append(
                cls(
                    id="fuming_potato_book",
                    display="Fuming Potato Books",
                    value=f_price * fpb_count,
                    debug_info={"count": fpb_count, "price_per": f_price},
                )
            )
        return None


class ItemFarmingForDummies(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.farming_for_dummies_count <= 0:
            return None
        value = await manager.get_price("farming_for_dummies", 0)
        item.calculations.append(
            cls(
                id="farming_for_dummies",
                display="Farming For Dummies",
                value=value * item.attributes.farming_for_dummies_count,
                debug_info={
                    "count": item.attributes.farming_for_dummies_count,
                    "price_per": value,
                },
            )
        )
        return None


class ItemJalapenoBooks(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.jalapeno_count <= 0:
            return None
        value = await manager.get_price("jalapeno_book", 0)
        item.calculations.append(
            cls(
                id="jalapeno_book",
                display="Jalapeno Books",
                value=value * item.attributes.jalapeno_count,
                debug_info={
                    "count": item.attributes.jalapeno_count,
                    "price_per": value,
                },
            )
        )
        return None


class ItemWoodSingularity(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.wood_singularity_count <= 0:
            return None
        value = await manager.get_price("wood_singularity", 0)
        item.calculations.append(
            cls(
                id="wood_singularity",
                display="Wood Singularity",
                value=value * item.attributes.wood_singularity_count,
                debug_info={
                    "count": item.attributes.wood_singularity_count,
                    "price_per": value,
                },
            )
        )
        return None


class ItemTransmissionTuners(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.tuned_transmission <= 0:
            return None
        value = await manager.get_price("transmission_tuner", 0)
        item.calculations.append(
            cls(
                id="transmission_tuner",
                display="Transmission Tuners",
                value=value * item.attributes.tuned_transmission,
                debug_info={
                    "count": item.attributes.tuned_transmission,
                    "price_per": value,
                },
            )
        )
        return None


class ItemManaDisintegrators(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.mana_disintegrator_count <= 0:
            return None
        value = await manager.get_price("mana_disintegrator", 0)
        item.calculations.append(
            cls(
                id="mana_disintegrator",
                display="Mana Disintegrators",
                value=value * item.attributes.mana_disintegrator_count,
                debug_info={
                    "count": item.attributes.mana_disintegrator_count,
                    "price_per": value,
                },
            )
        )
        return None


class ItemEthermergers(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or not item.attributes.ethermerge:
            return None
        value = await manager.get_price("ethermerger", 0)
        item.calculations.append(
            cls(
                id="ethermerge",
                display="Ethermerger",
                value=value,
            )
        )
        return None


class ItemBoosters(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or not item.attributes.boosters:
            return None
        calc = cls(
            id="boosters",
            display="Boosters",
            value=0,
            debug_info={"boosters": []},
        )
        for booster in item.attributes.boosters:
            price = await manager.get_price(booster.lower(), 0)
            calc.value += price
            calc.debug_info["boosters"].append({"id": booster, "price": price})
        item.calculations.append(calc)
        return None


class ItemCollectedCoins(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.collected_coins <= 0:
            return None
        value = item.attributes.collected_coins
        item.calculations.append(
            cls(
                id="collected_coins",
                display="Collected Coins",
                value=value,
            )
        )
        return None


class ItemDrillParts(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None:
            return None
        calc = cls(
            id="drill_parts",
            display="Drill Parts",
            value=0,
            debug_info={},
        )
        if item.attributes.drill_part_upgrade_module is not None:
            price = await manager.get_price(
                item.attributes.drill_part_upgrade_module.lower(), 0
            )
            calc.value += price
            calc.debug_info["upgrade_module"] = {
                "id": item.attributes.drill_part_upgrade_module,
                "price": price,
            }
        if item.attributes.drill_part_fuel_tank is not None:
            price = await manager.get_price(
                item.attributes.drill_part_fuel_tank.lower(), 0
            )
            calc.value += price
            calc.debug_info["fuel_tank"] = {
                "id": item.attributes.drill_part_fuel_tank,
                "price": price,
            }
        if item.attributes.drill_part_engine is not None:
            price = await manager.get_price(
                item.attributes.drill_part_engine.lower(), 0
            )
            calc.value += price
            calc.debug_info["engine"] = {
                "id": item.attributes.drill_part_engine,
                "price": price,
            }
        if calc.value > 0:
            item.calculations.append(calc)
        return None


class ItemBookOfStats(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or item.attributes.stats_book is None:
            return None
        if settings is not None and "cosmetic mods" not in settings:
            return None
        value = await manager.get_price("book_of_stats", 0)
        item.calculations.append(
            cls(
                id="book_of_stats",
                display="Book of Stats",
                value=value,
                debug_info={"book_of_stats": item.attributes.stats_book},
            )
        )
        return None


class ItemCakeBagCakes(ItemPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        item: "NetworthItem",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if item.attributes is None or not item.attributes.new_year_cake_bag_count:
            return None
        cake_count = item.attributes.new_year_cake_bag_count
        price = await manager.get_price("NEW_YEAR_CAKE", 0)
        calc = cls(
            id="new_year_cake_bag_count",
            display=f"{item.attributes.new_year_cake_bag_count}x New Years Cakes",
            value=price * cake_count,
            debug_info={"cakes": cake_count, "single": price},
        )
        item.calculations.append(calc)
        return None


# Pets
class PetPriceCalculation(PriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        pet: "NetworthPet",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None: ...


class PetBase(PetPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        pet: "NetworthPet",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        lvl1_price, lvl100_price, lvl200_price = await get_pet_prices_from_db(
            pet, manager
        )
        pet_skill = await pet_skill_level(pet.model_dump())
        pet.skykings_id = f"lvl_{int(pet_skill['level'])}_{pet.tier}_{pet.type}".lower()
        pet.display_name = (
            f"[Lvl {int(pet_skill['level'])}] "
            + (pet.tier + " " + pet.type).replace("_", " ").title()
            + (" ✦" if pet.skin is not None else "")
        )
        lvl1_price = (
            lvl1_price or lvl100_price
        )  # If a level 1 isnt there, just use lvl 100 as the base
        price_debug = {
            "lvl1_price": lvl1_price,
            "lvl100_price": lvl100_price,
            "lvl200_price": lvl200_price,
        }
        if lvl1_price is None:
            pet.calculations.append(
                cls(
                    id=pet.skykings_id,
                    display=pet.display_name,
                    value=0,
                    debug_info={
                        **pet.model_dump(),
                        **price_debug,
                        "details": "no price found",
                    },
                )
            )
            return None
        if pet_skill["level"] <= 100 and lvl100_price is not None:
            base_formula = (lvl100_price - lvl1_price) / 100
            price = base_formula * pet_skill["level"] + lvl1_price
            pet.calculations.append(
                cls(
                    id=pet.skykings_id,
                    display=pet.display_name,
                    value=int(price),
                    debug_info={
                        **pet.model_dump(),
                        **price_debug,
                        "details": "level <= 100",
                    },
                )
            )
            return None
        if 200 >= pet_skill["level"] > 100 and lvl200_price is not None:
            level = pet_skill["level"] - 100
            base_formula = (lvl200_price - lvl1_price) / 100
            price = base_formula * int(level) + lvl1_price
            pet.calculations.append(
                cls(
                    id=pet.skykings_id,
                    display=pet.display_name,
                    value=int(price),
                    debug_info={
                        **pet.model_dump(),
                        **price_debug,
                        "details": "100 < level <= 200",
                    },
                )
            )
            return None
        return None


class PetCandied(PetPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        pet: "NetworthPet",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if pet.candyUsed > 0 and pet.type != "ENDER_DRAGON":
            new_value = pet.value / 1.538232
            subtract = pet.value - new_value
            pet.calculations.append(
                cls(
                    id="candy_used",
                    display="Candy Used Reduction",
                    value=-int(subtract),
                    debug_info={"candy_used": pet.candyUsed},
                )
            )


class PetHeldItem(PetPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        pet: "NetworthPet",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if pet.heldItem is None:
            return None
        price = await manager.get_price(pet.heldItem.lower(), 0)
        pet.calculations.append(
            cls(
                id=pet.heldItem,
                display="Held Item",
                value=price,
                debug_info={"held_item": pet.heldItem},
            )
        )
        return None


class PetSkin(PetPriceCalculation):
    @classmethod
    async def calculate(
        cls,
        manager: "NetworthManager",
        pet: "NetworthPet",
        *,
        settings: "NetworthSettings | None" = None,
    ) -> None:
        if pet.skin is None:
            return None
        if settings is not None and "cosmetic mods" not in settings:
            return None
        price = await manager.get_price(f"pet_skin_{pet.skin.lower()}", default=0)
        pet.calculations.append(
            cls(
                id=pet.skin,
                display="Skin",
                value=price,
                debug_info={"skin": pet.skin},
            )
        )
        return None
