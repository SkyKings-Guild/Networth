from typing import Literal, NotRequired, Set, TypedDict

NetworthSettings = Set[
    Literal["cosmetics", "museum", "cosmetic mods", "hunting box", "attributes"]
]

Rarity = Literal["common", "uncommon", "rare", "epic", "legendary", "mythic", "special"]

class Enchantment(TypedDict):
    name: str
    id: str
    max_table: int
    max: int
    stacking: NotRequired[bool]
    upgrade_stones: NotRequired[dict[str, str]]


class Accessory(TypedDict):
    name: str
    rarity: Rarity
    upgrade: str | None
    rarity_upgradable: NotRequired[bool]
    removed: NotRequired[bool]
    rift: NotRequired[bool]
    duplicate: NotRequired[bool]



class GemstoneStats(TypedDict):
    ROUGH: dict[str, list[int | float | None]]
    FLAWED: dict[str, list[int | float | None]]
    FINE: dict[str, list[int | float | None]]
    FLAWLESS: dict[str, list[int | float | None]]
    PERFECT: dict[str, list[int | float | None]]


class Gemstone(TypedDict):
    name: str
    color: str
    stats: GemstoneStats


class AttributeShard(TypedDict):
    shard_name: str
    ability_name: str
    bazaar_id: str
    alignment: str
    rarity: Rarity
    family: list[str]
    misc_id: str


class UpgradeCost(TypedDict):
    ...

class EssenceUpgradeCost(UpgradeCost):
    type: Literal["ESSENCE"]
    essence_type: str
    amount: int

class ItemUpgradeCost(UpgradeCost):
    type: Literal["ITEM"]
    item_id: str
    amount: int


UpgradeCostUnion = EssenceUpgradeCost | ItemUpgradeCost


class GemstoneSlotUnlockCost(TypedDict):
    ...

class ItemGemstoneSlotUnlockCost(GemstoneSlotUnlockCost):
    type: Literal["ITEM"]
    item_id: str
    amount: int

class CoinGemstoneSlotUnlockCost(GemstoneSlotUnlockCost):
    type: Literal["COINS"]
    coins: int

GemstoneSlotUnlockCostUnion = ItemGemstoneSlotUnlockCost | CoinGemstoneSlotUnlockCost

class GemstoneSlot(TypedDict):
    slot_type: str
    costs: list[GemstoneSlotUnlockCostUnion]
