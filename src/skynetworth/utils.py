import math
import re
import asyncio
import base64
from io import BytesIO
from typing import cast

from nbt.nbt import NBTFile

from .types import NetworthSettings

__all__ = (
    "DEFAULT_NW_SETTINGS",
    "remove_minecraft_formatting",
    "to_roman_numerals",
    "parse_nbt",
    "cget",
    "human_number_format",
)

PET_LEVELING_DATA = {
    "levels": [
        100,
        110,
        120,
        130,
        145,
        160,
        175,
        190,
        210,
        230,
        250,
        275,
        300,
        330,
        360,
        400,
        440,
        490,
        540,
        600,
        660,
        730,
        800,
        880,
        960,
        1050,
        1150,
        1260,
        1380,
        1510,
        1650,
        1800,
        1960,
        2130,
        2310,
        2500,
        2700,
        2920,
        3160,
        3420,
        3700,
        4000,
        4350,
        4750,
        5200,
        5700,
        6300,
        7000,
        7800,
        8700,
        9700,
        10800,
        12000,
        13300,
        14700,
        16200,
        17800,
        19500,
        21300,
        23200,
        25200,
        27400,
        29800,
        32400,
        35200,
        38200,
        41400,
        44800,
        48400,
        52200,
        56200,
        60400,
        64800,
        69400,
        74200,
        79200,
        84700,
        90700,
        97200,
        104200,
        111700,
        119700,
        128200,
        137200,
        146700,
        156700,
        167700,
        179700,
        192700,
        206700,
        221700,
        237700,
        254700,
        272700,
        291700,
        311700,
        333700,
        357700,
        383700,
        411700,
        441700,
        476700,
        516700,
        561700,
        611700,
        666700,
        726700,
        791700,
        861700,
        936700,
        1016700,
        1101700,
        1191700,
        1286700,
        1386700,
        1496700,
        1616700,
        1746700,
        1886700,
        0,
        1,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
        1886700,
    ],
    "rarity_offset": {
        "COMMON": 0,
        "UNCOMMON": 6,
        "RARE": 11,
        "EPIC": 16,
        "LEGENDARY": 20,
        "MYTHIC": 20,
        "SPECIAL": 16,
        "VERY_SPECIAL": 20,
    },
}
MINECRAFT_FMT_REGEX = re.compile(r"§[a-z\d]")

#: Settings enabled by default when evaluating a profile's networth.
DEFAULT_NW_SETTINGS: NetworthSettings = {
    "museum",
    "cosmetics",
    "cosmetic mods",
    "hunting box",
}


def _calculate_level(
    xp: float, levels: list[float] | list[int], *, remove_xp: bool = True
) -> float:
    """
    Calculate the level of something based on its experience points and the leveling table.

    :param xp: The experience points of the thing.
    :param levels: The leveling table.
    :param remove_xp: Whether to remove the experience points from the total when calculating the level.
    :return: The level of the thing.
    """
    lvl = 0
    rexp = xp
    for level in levels:
        if rexp >= level:
            if remove_xp:
                rexp -= level
            lvl += 1
        elif rexp < level:
            lvl += rexp / level
            break
    return lvl


async def pet_skill_level(pet: dict) -> dict[str, int | float]:
    """
    Calculate the level of a pet.

    :param pet: The pet data.
    :return: A dictionary containing the maximum experience points and the level of the pet.
    """
    maxlevel = (
        200 if pet["type"] in ("GOLDEN_DRAGON", "JADE_DRAGON", "ROSE_DRAGON") else 100
    )
    rarity_offset = PET_LEVELING_DATA["rarity_offset"][pet["tier"]]
    levels: list[int] = cast(
        list[int],
        PET_LEVELING_DATA["levels"][rarity_offset : rarity_offset + maxlevel - 1],
    )  # type: ignore
    level = _calculate_level(pet.get("exp", 0), levels) + 1
    return {"xpMax": sum(levels), "level": min(level, maxlevel)}


def remove_minecraft_formatting(text: str) -> str:
    """
    Remove Minecraft formatting codes from a string.

    :param text: The string to remove formatting codes from.
    :return: The string with formatting codes removed.
    """
    return MINECRAFT_FMT_REGEX.sub("", text)


def to_roman_numerals(number: int) -> str:
    """
    Convert an integer to a Roman numeral.

    :param number: The integer to convert. Must be between 1 and 3999.
    :return: The Roman numeral representation of the integer.
    """
    if not (0 < number < 4000):
        raise ValueError("Number must be between 1 and 3999")
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ""
    for i in range(len(val)):
        count = number // val[i]
        roman_num += syms[i] * count
        number -= val[i] * count
    return roman_num


def _parse(nbt_data: str | bytes, decode_b64: bool=True) -> NBTFile:

    if decode_b64:
        nbt_data = base64.b64decode(nbt_data)
    data: NBTFile = NBTFile(fileobj=BytesIO(nbt_data))
    return data


async def parse_nbt(nbt_data: str | bytes, *, loop: asyncio.AbstractEventLoop | None=None, decode_b64: bool=True) -> NBTFile:
    """
    Parse NBT data from a string or bytes asynchronously.

    :param nbt_data: The NBT data to parse. Can be a string or bytes.
    :param loop: The event loop to use for asynchronous execution. If None, the default event loop will be used.
    :param decode_b64: Whether to decode the NBT data from base64. Defaults to True.
    :return: The parsed NBT data as an NBTFile object.
    """
    if loop is None:
        loop = asyncio.get_event_loop()
    data: NBTFile = await loop.run_in_executor(None, _parse, nbt_data, decode_b64)
    return data


def cget(dictionary, *args, default=None):
    """
    Get a value from a nested dictionary using a sequence of keys.

    :param dictionary: The dictionary to get the value from.
    :param args: A sequence of keys to traverse the nested dictionary.
    :param default: The default value to return if the key is not found. Defaults to None.
    :return: The value from the nested dictionary, or the default value if the key is not found.
    """
    if dictionary is None:
        return default
    result = dictionary
    for item in args:
        if not hasattr(result, "get"):
            return default
        result = result.get(item, default)
    return result


def human_number_format(number):
    """
    Format a number into a human-readable string with suffixes (K, M, B, T).

    :param number: The number to format.
    :return: A string representing the formatted number with appropriate suffixes.
    """
    number = int(round(number, 0))
    if number == 0:
        return "0"
    if number < 0:
        return "-" + human_number_format(-number)
    units = ["", "K", "M", "B", "T"]
    k = 1000
    magnitude = min(int(math.floor(math.log(number, k))), len(units) - 1)
    num = round(number / k**magnitude, 2)
    if num == int(num):
        num = int(num)
    return f"{num:,}{units[magnitude]}"
