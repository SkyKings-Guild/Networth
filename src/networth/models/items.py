from typing import TYPE_CHECKING, Self, overload

from nbt.nbt import TAG_Compound, TAG_List
from pydantic import Field, BaseModel as Model

from .profile import Pet
from ..calculators import PriceCalculation
from ..types import NetworthSettings
from ..utils import parse_nbt, cget, human_number_format, remove_minecraft_formatting

if TYPE_CHECKING:
    from ..manager import NetworthManager

__all__ = (
    "NetworthSettings",
    "ItemGem",
    "ItemAttributes",
    "ItemDisplay",
    "NetworthItem",
    "NetworthPet",
    "ParsedGemstone",
)

class FNBT:
    def __init__(self, value):
        self.value = value


class ItemGem(Model):
    quality: str


class ItemAttributes(Model):
    id: str = ""
    donated_museum: bool = False
    # Cosmetics
    skin: str | None = None
    dye: str | None = None
    runes: dict[str, int] = Field(default_factory=dict)
    # Applied Items
    upgrade_level: int = 0
    gemstone_slots: int = 0
    rarity_upgrades: int = 0
    talisman_enrichment: str | None = None
    modifier: str | None = None
    art_of_peace_applied: bool = False
    jalapeno_count: int = 0
    art_of_war_count: int = 0
    hot_potato_count: int = 0
    stats_book: int | None = None
    farming_for_dummies_count: int = 0
    mana_disintegrator_count: int = 0
    wood_singularity_count: int = 0
    tuned_transmission: int = 0
    ability_scrolls: list[str] = Field(default_factory=list)
    power_ability_scroll: str | None = None
    boosters: list[str] = Field(default_factory=list)
    enchantments: dict[str, int] = Field(default_factory=dict)
    gems: dict[str, str | list[str] | ItemGem] = Field(default_factory=dict)
    ethermerge: bool = False
    # Counters
    collected_coins: int = 0  # Crown of Avarice
    # Drill Parts
    drill_part_upgrade_module: str | None = None
    drill_part_fuel_tank: str | None = None
    drill_part_engine: str | None = None
    # Shen's Auction Price
    price: int | None = None
    soulbound: bool = False
    # Cake Bag
    new_year_cake_bag_count: int | None = None


class ItemDisplay(Model):
    name: str
    # lore: list[str]


async def nget(nbt: TAG_Compound, *keys, default=None):
    """Get a value from a nested NBT structure using a list of keys."""
    current = nbt
    for key in keys:
        if isinstance(current, TAG_Compound) and key in current:
            current = current[key]
        else:
            return default
    if isinstance(current, TAG_List):
        return [
            tag.value if not isinstance(tag, TAG_Compound) else await dictify(tag)
            for tag in current
        ]
    if isinstance(current, TAG_Compound):
        return await dictify(current)
    return current.value


@overload
async def dictify(nbt: None) -> None: ...


@overload
async def dictify(nbt: TAG_Compound) -> dict: ...


@overload
async def dictify(nbt: TAG_List) -> list: ...


async def dictify(nbt: TAG_Compound | TAG_List | None) -> dict | list | None:
    """Convert a TAG_Compound to a dictionary."""
    if nbt is None:
        return None
    if isinstance(nbt, TAG_List):
        return [
            await dictify(tag) if isinstance(tag, TAG_Compound) else tag.value
            for tag in nbt.tags
        ]
    result = {}
    for tag in nbt.tags:
        if isinstance(tag, (TAG_Compound, TAG_List)):
            result[tag.name] = await dictify(tag)
        else:
            if isinstance(tag.value, (bytes, bytearray)):
                # parse to nbt
                result[tag.name] = await dictify(
                    (await parse_nbt(tag.value, decode_b64=False))["i"]
                )
            else:
                result[tag.name] = tag.value
    return result


class NetworthItem(Model):
    minecraft_id: int
    count: int = 0
    display: ItemDisplay | None = None
    attributes: ItemAttributes | None = None
    raw_nbt: dict | None = None
    calculations: list[PriceCalculation] = Field(default_factory=list)
    tooltip_style: str | None = None

    @classmethod
    async def from_nbt(cls, nbt: TAG_Compound) -> Self:
        exa = cget(nbt, "tag", "ExtraAttributes", default=None)
        return cls(
            minecraft_id=await nget(nbt, "id", default=0),
            count=await nget(nbt, "Count", default=0),
            display=ItemDisplay(
                name=await nget(nbt, "tag", "display", "Name", default=""),
                # lore=await nget(nbt, "tag", "display", "Lore", default=[]),
            ),
            tooltip_style=await nget(
                nbt, "components", "minecraft:tooltip_style", default=None
            ),
            attributes=ItemAttributes(
                id=await nget(exa, "id", default=""),
                donated_museum=bool(await nget(exa, "donated_museum", default=False)),
                skin=await nget(exa, "skin", default=None),
                enchantments=await nget(exa, "enchantments", default={}),
                rarity_upgrades=await nget(exa, "rarity_upgrades", default=0),
                talisman_enrichment=await nget(exa, "talisman_enrichment"),
                gems=await nget(exa, "gems", default={}),
                modifier=await nget(exa, "modifier"),
                dye=await nget(exa, "dye_item"),
                runes=await nget(exa, "runes", default={}),
                art_of_peace_applied=bool(
                    await nget(exa, "artOfPeaceApplied", default=False)
                ),
                upgrade_level=await nget(exa, "upgrade_level", default=0),
                ability_scrolls=await nget(exa, "ability_scroll", default=[]),
                power_ability_scroll=await nget(
                    exa, "power_ability_scroll", default=None
                ),
                gemstone_slots=await nget(exa, "gemstone_slots", default=0),
                art_of_war_count=await nget(exa, "art_of_war_count", default=0),
                hot_potato_count=await nget(exa, "hot_potato_count", default=0),
                stats_book=await nget(exa, "stats_book", default=None),
                farming_for_dummies_count=await nget(
                    exa, "farming_for_dummies_count", default=0
                ),
                wood_singularity_count=await nget(
                    exa, "wood_singularity_count", default=0
                ),
                tuned_transmission=await nget(exa, "tuned_transmission", default=0),
                boosters=await nget(exa, "boosters", default=[]),
                jalapeno_count=await nget(exa, "jalapeno_count", default=0),
                mana_disintegrator_count=await nget(
                    exa, "mana_disintegrator_count", default=0
                ),
                collected_coins=await nget(exa, "collected_coins", default=0),
                soulbound=bool(await nget(exa, "soulbound", default=False)),
                drill_part_upgrade_module=await nget(exa, "drill_part_upgrade_module"),
                drill_part_fuel_tank=await nget(exa, "drill_part_fuel_tank"),
                drill_part_engine=await nget(exa, "drill_part_engine"),
                ethermerge=bool(await nget(exa, "ethermerge", default=False)),
                price=await nget(exa, "price", default=None),
                new_year_cake_bag_count=len(
                    await nget(exa, "new_year_cake_bag_data", default=[])
                ),
            )
            if exa is not None
            else None,
            raw_nbt=await dictify(nbt),
        )

    @property
    def item_id(self) -> str:
        return self.attributes.id if self.attributes else "MC:" + str(self.minecraft_id)

    @property
    def item_name(self) -> str:
        return self.display.name if self.display else self.item_id

    @property
    def recombobulated(self) -> bool:
        if self.attributes is None:
            return False
        return self.attributes.rarity_upgrades > 0

    @property
    def individual_value(self) -> int:
        return sum(calc.value for calc in self.calculations)

    @property
    def value(self) -> int:
        return self.individual_value * self.count

    def reset(self) -> None:
        self.calculations.clear()

    async def should_evaluate(
        self, manager: "NetworthManager", settings: NetworthSettings | None = None
    ) -> bool:
        if (
            # this was changed because items that are permanently soulbound inherently have no value
            # since they cannot be sold, and it is very hard to determine price data for a soulbound item
            # so we just exclude them
            # "soulbound" not in settings and
            self.item_id.upper() in await manager.soulbound_items()
            or (self.attributes and self.attributes.soulbound)
        ):
            return False
        if settings is None:
            return True
        if (
            "museum" not in settings
            and self.attributes
            and self.attributes.donated_museum
        ):
            return False
        if (
            "cosmetics" not in settings
            and self.item_id.upper() in await manager.cosmetic_items()
        ):
            return False
        return True


class NetworthPet(Pet):
    display_name: str | None = None
    skykings_id: str | None = None
    calculations: list[PriceCalculation] = Field(default_factory=list)

    @property
    def item_id(self) -> str:
        if self.skykings_id is None:
            return ""
        return self.skykings_id

    @property
    def item_name(self) -> str:
        return self.display_name if self.display_name else self.type

    @property
    def recombobulated(self) -> bool:
        return False

    @property
    def value(self) -> int:
        return sum(calc.value for calc in self.calculations)

    def reset(self) -> None:
        self.display_name = None
        self.skykings_id = None
        self.calculations.clear()

    async def should_evaluate(
        self, manager: "NetworthManager", settings: NetworthSettings | None = None
    ) -> bool:
        return True


class ParsedGemstone(Model):
    type: str
    tier: str
