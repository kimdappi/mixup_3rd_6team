from app.services.address_parser import parse_address


def test_parse_seoul_gangseo_address():
    result = parse_address("서울 강서구 가양동 강변아파트")

    assert result.normalized_address == "서울특별시 강서구 가양동 강변아파트"
    assert result.lawd_cd == "11500"
    assert result.dong == "가양동"
    assert result.apt_keyword == "강변아파"


def test_parse_gyeonggi_suwon_address_long_key_first():
    result = parse_address("경기 수원시 장안구 정자동")

    assert result.normalized_address == "경기도 수원시 장안구 정자동"
    assert result.lawd_cd == "41111"
    assert result.dong == "정자동"
