from app.clients.molit import RentTransaction
from app.services.market_filter import select_market_scope


def test_selects_complex_scope_when_three_complex_matches():
    items = [
        RentTransaction("강변아파트", "가양동", 50.0, "1", 250_000_000, "2024", "10"),
        RentTransaction("강변아파트", "가양동", 51.0, "2", 260_000_000, "2024", "11"),
        RentTransaction("강변아파트", "가양동", 49.0, "3", 255_000_000, "2024", "12"),
        RentTransaction("다른아파트", "가양동", 50.0, "4", 200_000_000, "2024", "12"),
    ]

    result = select_market_scope(items, dong="가양동", apt_keyword="강변아파", area_sqm=50.0)

    assert result.scope == "complex"
    assert len(result.items) == 3


def test_falls_back_to_gu_all_when_area_matches_are_insufficient():
    items = [
        RentTransaction("A", "가양동", 80.0, "1", 250_000_000, "2024", "10"),
        RentTransaction("B", "가양동", 85.0, "2", 260_000_000, "2024", "11"),
        RentTransaction("C", "등촌동", 90.0, "3", 255_000_000, "2024", "12"),
    ]

    result = select_market_scope(items, dong="가양동", apt_keyword="강변아파", area_sqm=50.0)

    assert result.scope == "gu_all"
    assert len(result.items) == 3
