from fastapi.testclient import TestClient

from app.main import app


def test_full_endpoint_exists():
    client = TestClient(app)
    response = client.post(
        "/diagnoses/full",
        data={
            "address": "서울 강서구 가양동 강변아파트",
            "area_sqm": "50.0",
            "user_deposit": "250000000",
            "housing_type": "apartment",
            "contract_stage": "before_contract",
        },
        files={"registry_document": ("registry.txt", "근저당".encode("utf-8"), "text/plain")},
    )

    assert response.status_code in (200, 503)
