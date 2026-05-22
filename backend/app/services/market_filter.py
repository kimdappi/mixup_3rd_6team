from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar


class AreaNamedTransaction(Protocol):
    name: str
    dong: str
    area: float


T = TypeVar("T", bound=AreaNamedTransaction)


@dataclass(frozen=True)
class ScopedTransactions(Generic[T]):
    scope: str
    items: list[T]


def filter_by_area(items: list[T], area_sqm: float, tolerance: float = 0.20) -> list[T]:
    if not area_sqm or area_sqm <= 0:
        return items
    return [item for item in items if abs(item.area - area_sqm) / area_sqm <= tolerance]


def select_market_scope(items: list[T], dong: str | None, apt_keyword: str | None, area_sqm: float) -> ScopedTransactions[T]:
    if apt_keyword and dong:
        complex_items = [item for item in items if item.dong == dong and item.name.startswith(apt_keyword)]
        complex_area_items = filter_by_area(complex_items, area_sqm)
        if len(complex_area_items) >= 3:
            return ScopedTransactions(scope="complex", items=complex_area_items)

    if dong:
        dong_items = [item for item in items if item.dong == dong]
        dong_area_items = filter_by_area(dong_items, area_sqm)
        if len(dong_area_items) >= 3:
            return ScopedTransactions(scope="dong", items=dong_area_items)

    gu_area_items = filter_by_area(items, area_sqm)
    if len(gu_area_items) >= 3:
        return ScopedTransactions(scope="gu", items=gu_area_items)

    return ScopedTransactions(scope="gu_all", items=items)
