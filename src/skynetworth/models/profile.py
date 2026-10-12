from typing import Any, Literal

from pydantic import Field, BaseModel as Model


class EssenceCurrencyInfo(Model):
    current: int = 0


class ProfileMemberCurrencyInfo(Model):
    coin_purse: float
    motes_purse: float = 0.0
    essence: dict[str, EssenceCurrencyInfo] = Field(default_factory=dict)


class ProfileMemberProfileInfo(Model):
    first_join: int | None = None
    personal_bank_upgrade: int = 0
    bank_account: float | None = None
    cookie_buff_active: bool = False


class InventoryData(Model):
    type: int
    data: str


class BagContents(Model):
    potion_bag: InventoryData | None = None
    talisman_bag: InventoryData | None = None
    fishing_bag: InventoryData | None = None
    sacks_bag: InventoryData | None = None
    quiver: InventoryData | None = None


class ProfileMemberInventoryInfo(Model):
    inv_contents: InventoryData | None = None
    ender_chest_contents: InventoryData | None = None
    backpack_icons: dict[str, InventoryData] | None = None
    bag_contents: BagContents | None = None
    inv_armor: InventoryData | None = None
    equipment_contents: InventoryData | None = None
    personal_vault_contents: InventoryData | None = None
    wardrobe_equipped_slot: int | None = None
    backpack_contents: dict[str, InventoryData] | None = None
    sacks_counts: dict[str, int] | None = None


class Pet(Model):
    uuid: str | None = None
    uniqueId: str | None = None
    type: str
    exp: float
    active: bool = False
    tier: str
    heldItem: str | None = None
    candyUsed: int = 0
    skin: str | None = None


class ProfileMemberPetInfo(Model):
    pets: list[Pet] = Field(default_factory=list)


class LoadoutInfo(Model):
    armor: dict[str, int | dict[str, InventoryData | int]] | None = None
    equipment: dict[str, int | dict[str, InventoryData | int]] | None = None


class ProfileMemberAttributesInfo(Model):
    stacks: dict[str, int] | None = None


class AttributeShard(Model):
    type: str
    amount_owned: int


class ProfileMemberShardsInfo(Model):
    owned: list[AttributeShard] | None = None


class SkyBlockProfileMember(Model):
    currencies: ProfileMemberCurrencyInfo | None = None
    inventory: ProfileMemberInventoryInfo | None = None
    pets_data: ProfileMemberPetInfo | None = None
    loadout: LoadoutInfo | None = None
    profile: ProfileMemberProfileInfo
    attributes: ProfileMemberAttributesInfo | None = None
    shards: ProfileMemberShardsInfo | None = None


class BankTransaction(Model):
    amount: float
    timestamp: int
    action: Literal["DEPOSIT", "WITHDRAW"]
    initiator_name: str


class SkyBlockBankingData(Model):
    balance: float
    transactions: list[BankTransaction]


class SkyBlockProfile(Model):
    profile_id: str
    members: dict[str, SkyBlockProfileMember]
    banking: SkyBlockBankingData | None = None
    cute_name: str
    selected: bool = False
