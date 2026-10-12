from abc import ABC, abstractmethod
from typing import Any, overload, TypeVar


class PriceProvider(ABC):
    @overload
    async def get_price(self, item_id: str) -> int:
        ...

    @overload
    async def get_price(self, item_id: str, default: int) -> int:
        ...

    @overload
    async def get_price(self, item_id: str, default: None) -> int | None:
        ...

    @abstractmethod
    async def get_price(self, item_id: str, default: int | None = 0) -> int | None:
        """Get the price of an item by its ID."""
        ...

class DictPriceProvider(PriceProvider):
    def __init__(self, prices: dict[str, int]):
        self.prices = {k.lower(): v for k, v in prices.items()}

    async def get_price(self, item_id: str, default: int | None = 0) -> int | None:
        return self.prices.get(item_id.lower(), default)