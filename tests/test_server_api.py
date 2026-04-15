from app.schemas import DiagnosticReport


def test_diagnose_requires_api_key(client):
    response = client.post("/diagnose", json={"log_text": "ERROR x", "image_base64": ""})
    assert response.status_code == 401


def test_diagnose_rejects_invalid_api_key(client):
    response = client.post(
        "/diagnose",
        headers={"X-API-Key": "wrong-key"},
        json={"log_text": "ERROR x", "image_base64": ""},
    )
    assert response.status_code == 401


def test_diagnose_returns_mocked_report(client, server_module, valid_api_key, monkeypatch):
    mocked_report = DiagnosticReport(
        severity="High",
        root_cause="mocked root cause",
        suggested_fix="mocked fix",
        related_files=["app/server.py"],
        confidence=0.8,
    )

    def fake_analyze_log_with_gemma(log_text: str, image_base64: str = "") -> DiagnosticReport:
        return mocked_report

    monkeypatch.setattr(server_module, "analyze_log_with_gemma", fake_analyze_log_with_gemma)

    response = client.post(
        "/diagnose",
        headers={"X-API-Key": valid_api_key},
        json={"log_text": "ERROR x", "image_base64": ""},
    )

    assert response.status_code == 200
    assert response.json() == mocked_report.model_dump()


def test_openapi_hides_langserve_internal_routes(server_module):
    schema = server_module.app.openapi()
    assert "/diagnose" in schema["paths"]
    assert all(not path.startswith("/analyze_raw") for path in schema["paths"])
