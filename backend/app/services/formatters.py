"""금액 자연 표기 포매터.

전제: 입력은 **만원 단위 정수**.
원 단위 값을 가진 호출부는 반드시 `won // 10000`으로 변환해서 넘길 것.
"""


def format_won(amount) -> str:
    """만원 단위 정수를 한국어 자연 표기로 변환.

    예시:
        None     -> "0원"
        0        -> "0원"
        9500     -> "9,500만원"
        10000    -> "1억"
        10500    -> "1억 500만원"
        104783   -> "10억 4,783만원"
        230000   -> "23억"
    """
    if amount is None:
        return "0원"

    try:
        amount = int(amount)
    except (ValueError, TypeError):
        return "0원"

    if amount == 0:
        return "0원"
    if amount < 10000:
        return f"{amount:,}만원"

    eok = amount // 10000
    man = amount % 10000

    if man == 0:
        return f"{eok}억"
    return f"{eok}억 {man:,}만원"
