from app.clients.molit import RentTransaction, TradeTransaction
from app.services.market_diagnosis import diagnose_market


def test_diagnose_market_calculates_rates_and_high_risk():
    rents = [
        RentTransaction("강변아파트", "가양동", 50.0, "1", 250_000_000, "2024", "10"),
        RentTransaction("강변아파트", "가양동", 51.0, "2", 260_000_000, "2024", "11"),
        RentTransaction("강변아파트", "가양동", 49.0, "3", 255_000_000, "2024", "12"),
    ]
    trades = [
        TradeTransaction("강변아파트", "가양동", 50.0, "5", 300_000_000, "2024", "10"),
        TradeTransaction("강변아파트", "가양동", 51.0, "6", 310_000_000, "2024", "11"),
        TradeTransaction("강변아파트", "가양동", 49.0, "7", 305_000_000, "2024", "12"),
    ]

    result = diagnose_market(
        address="서울 강서구 가양동 강변아파트",
        user_deposit=250_000_000,
        rent_scope="complex",
        rents=rents,
        trade_scope="complex",
        trades=trades,
    )

    assert result.market_analysis.user_jeonse_rate is not None
    assert result.market_analysis.gangtong_risk == "high"
    assert result.market_analysis.jeonse_count == 3
    assert result.market_analysis.trade_count == 3


def test_diagnose_market_handles_missing_sale_data():
    rents = [
        RentTransaction("강변아파트", "가양동", 50.0, "1", 250_000_000, "2024", "10"),
        RentTransaction("강변아파트", "가양동", 51.0, "2", 260_000_000, "2024", "11"),
        RentTransaction("강변아파트", "가양동", 49.0, "3", 255_000_000, "2024", "12"),
    ]

    result = diagnose_market(
        address="서울 강서구 가양동 강변아파트",
        user_deposit=250_000_000,
        rent_scope="complex",
        rents=rents,
        trade_scope="gu_all",
        trades=[],
    )

    assert result.market_analysis.gangtong_risk == "null"
    assert result.market_analysis.user_jeonse_rate is None
    assert any(signal.code == "NO_SALE_TRANSACTION_DATA" for signal in result.risk_signals)
