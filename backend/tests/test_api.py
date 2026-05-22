from fastapi.testclient import TestClient

from app.main import app


def test_health_check():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_quick_diagnosis_accepts_payload():
    client = TestClient(app)
    payload = {
        "address": "서울 강서구 가양동 강변아파트",
        "area_sqm": 50.0,
        "user_deposit": 250000000,
        "housing_type": "apartment",
        "contract_stage": "before_contract",
    }

    response = client.post("/diagnoses/quick", json=payload)

    assert response.status_code in (200, 503)
