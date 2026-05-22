from app.clients.llm import FakeLLMClient, ReportGenerationInput


def test_fake_llm_client_returns_stable_report_text():
    client = FakeLLMClient()
    result = client.generate_report(
        ReportGenerationInput(
            address="서울 강서구 가양동 강변아파트",
            risk_signals=[],
            missing_information=[],
        )
    )

    assert result.summary
    assert "사전진단" in result.disclaimer
