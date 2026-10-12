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
        1886700
    ],
    "rarity_offset": {
        "COMMON": 0,
        "UNCOMMON": 6,
        "RARE": 11,
        "EPIC": 16,
        "LEGENDARY": 20,
        "MYTHIC": 20,
        "SPECIAL": 16,
        "VERY_SPECIAL": 20
    }
}
MINECRAFT_FMT_REGEX = re.compile(r"§[a-z\d]")
DEFAULT_NW_SETTINGS: NetworthSettings = {
    "museum",
    "cosmetics",
    "cosmetic mods",
    "hunting box",
}

def _calculate_level(
    xp: float, levels: list[float] | list[int], *, remove_xp: bool = True
) -> float:
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
    maxlevel = (
        200 if pet["type"] in ("GOLDEN_DRAGON", "JADE_DRAGON", "ROSE_DRAGON") else 100
    )
    rarity_offset = PET_LEVELING_DATA["rarity_offset"][pet["tier"]]
    levels: list[int] = cast(list[int], PET_LEVELING_DATA["levels"][rarity_offset : rarity_offset + maxlevel - 1])  # type: ignore
    level = _calculate_level(pet.get("exp", 0), levels) + 1
    return {"xpMax": sum(levels), "level": min(level, maxlevel)}

def remove_minecraft_formatting(text: str) -> str:
    return MINECRAFT_FMT_REGEX.sub("", text)


def to_roman_numerals(number: int) -> str:
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


def _parse(nbt_data, decode_b64=True):
    if decode_b64:
        nbt_data = base64.b64decode(nbt_data)
    data: NBTFile = NBTFile(fileobj=BytesIO(nbt_data))
    return data


async def parse_nbt(nbt_data, *, loop=None, decode_b64=True):
    if loop is None:
        loop = asyncio.get_event_loop()
    data: NBTFile = await loop.run_in_executor(None, _parse, nbt_data, decode_b64)
    return data

def cget(dictionary, *args, default=None):
    if dictionary is None:
        return default
    result = dictionary
    for item in args:
        if not hasattr(result, "get"):
            return default
        result = result.get(item, default)
    return result


def human_number_format(number):
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
