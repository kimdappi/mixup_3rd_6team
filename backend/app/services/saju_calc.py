# backend/app/services/saju_calc.py
from sajupy import calculate_saju

# 천간 → 오행 매핑
CHEONGAN_OHENG = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}

# 지지 → 오행 매핑
JIJI_OHENG = {
    "寅": "木", "卯": "木",
    "巳": "火", "午": "火",
    "辰": "土", "未": "土", "戌": "土", "丑": "土",
    "申": "金", "酉": "金",
    "亥": "水", "子": "水",
}

def calculate(year, month, day, hour, minute, city="Seoul"):
    """
    sajupy로 사주 계산 → 팔자 문자열 + 오행 카운트 반환
    """
    # 1. sajupy 호출 (태양시 보정 ON)
    result = calculate_saju(
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        city=city,
        use_solar_time=True,
    )

    # 2. 8글자 추출 (천간 4개 + 지지 4개)
    stems = [
        result["year_stem"],
        result["month_stem"],
        result["day_stem"],
        result["hour_stem"],
    ]
    branches = [
        result["year_branch"],
        result["month_branch"],
        result["day_branch"],
        result["hour_branch"],
    ]

    # 3. 오행 카운트
    oheng_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for stem in stems:
        oheng = CHEONGAN_OHENG.get(stem)
        if oheng:
            oheng_count[oheng] += 1
    for branch in branches:
        oheng = JIJI_OHENG.get(branch)
        if oheng:
            oheng_count[oheng] += 1

    # 4. 팔자 문자열 조합
    pillars_str = (
        f"{result['year_pillar']}年 "
        f"{result['month_pillar']}月 "
        f"{result['day_pillar']}日 "
        f"{result['hour_pillar']}時"
    )

    return {
        "pillars": pillars_str,
        "oheng_count": oheng_count,
    }
