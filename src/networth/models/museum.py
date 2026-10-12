from pydantic import Field, BaseModel as Model

from .profile import InventoryData


class MuseumItem(Model):
    donated_time: int
    featured_slot: str | None = None
    borrowing: bool = False
    items: InventoryData | None = None


class MuseumMemberData(Model):
    value: int | None = None
    appraisal: bool = False
    items: dict[str, MuseumItem] = Field(default_factory=dict)
    special: list[MuseumItem] = Field(default_factory=list)
