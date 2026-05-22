from datetime import date

from app.clients.molit import normalize_rent_items, normalize_trade_items, recent_deal_months


def test_normalize_rent_items_filters_monthly_rent_and_converts_to_won():
    raw = [
        {"aptNm": "강변아파트", "umdNm": "가양동", "excluUseAr": "50.0", "deposit": "25,000", "monthlyRent": "0", "floor": "3", "dealYear": "2024", "dealMonth": "11"},
        {"aptNm": "월세아파트", "umdNm": "가양동", "excluUseAr": "50.0", "deposit": "1,000", "monthlyRent": "50", "floor": "4", "dealYear": "2024", "dealMonth": "11"},
    ]

    result = normalize_rent_items(raw)

    assert len(result) == 1
    assert result[0].deposit == 250_000_000


def test_normalize_trade_items_filters_cancelled_and_converts_to_won():
    raw = [
        {"aptNm": "강변아파트", "umdNm": "가양동", "excluUseAr": "50.0", "dealAmount": "45,000", "dealingGbn": "", "floor": "5", "dealYear": "2024", "dealMonth": "10"},
        {"aptNm": "취소아파트", "umdNm": "가양동", "excluUseAr": "50.0", "dealAmount": "40,000", "dealingGbn": "Y", "floor": "5", "dealYear": "2024", "dealMonth": "10"},
    ]

    result = normalize_trade_items(raw)

    assert len(result) == 1
    assert result[0].price == 450_000_000


def test_recent_deal_months_rolls_back_across_year():
    assert recent_deal_months(date(2026, 1, 15), months=3) == ["202601", "202512", "202511"]
