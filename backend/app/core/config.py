import os
from dotenv import load_dotenv

load_dotenv()

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
SOLAR_PRO_API_KEY = os.getenv("SOLAR_PRO_API_KEY", "")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
MOLIT_API_SERVICE_KEY = os.getenv("MOLIT_API_SERVICE_KEY", "")
# 매매 API용 별도 키. 비어 있으면 MOLIT_API_SERVICE_KEY로 폴백된다.
# (data.go.kr이 한 계정 한 키 정책이라 보통은 같은 값이지만,
#  활용신청 분리로 두 키가 다를 수 있다.)
MOLIT_API_TRADE_SERVICE_KEY = os.getenv("MOLIT_API_TRADE_SERVICE_KEY", "")
