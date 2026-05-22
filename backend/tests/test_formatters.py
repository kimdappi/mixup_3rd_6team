"""format_won 자연 표기 단위 테스트 (v3.1).

입력 단위는 만원이라는 전제로 검증.
"""
from app.services.formatters import format_won


def test_format_won_none():
    assert format_won(None) == "0원"


def test_format_won_zero():
    assert format_won(0) == "0원"


def test_format_won_under_eok():
    assert format_won(9500) == "9,500만원"


def test_format_won_exact_eok():
    assert format_won(10000) == "1억"


def test_format_won_with_remainder():
    assert format_won(10500) == "1억 500만원"


def test_format_won_large():
    assert format_won(104783) == "10억 4,783만원"


def test_format_won_exact_multi_eok():
    assert format_won(230000) == "23억"


def test_format_won_invalid_type():
    assert format_won("abc") == "0원"


def test_format_won_small_amount():
    assert format_won(5) == "5만원"


def test_format_won_string_int_parse():
    """문자열로 들어와도 int 파싱 가능하면 동작."""
    assert format_won("10500") == "1억 500만원"
