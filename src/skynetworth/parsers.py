from .models import NetworthItem
from .utils import cget, parse_nbt

__all__ = ("parse_inventory",)


async def parse_inventory(inventory_data: str) -> list["NetworthItem"]:
    """
    Parse an inventory data string into a list of NetworthItem objects.

    :param inventory_data: A string containing the inventory data in NBT format.
    :return: A list of NetworthItem objects parsed from the inventory data.
    """
    return [
        await NetworthItem.from_nbt(item)
        for item in (await parse_nbt(inventory_data))["i"]
        if cget(item, "tag", "ExtraAttributes", default=None) is not None
    ]
