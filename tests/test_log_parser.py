from app.logic.log_parser import clean_log_text, extract_critical_sections


def test_clean_log_text_redacts_common_sensitive_values():
    raw = (
        "User path: /Users/alice/project\n"
        "Windows path: C:\\Users\\alice\\project\\main.py\n"
        "Email: alice@example.com\n"
        "api_key=abc123xyz\n"
    )

    cleaned = clean_log_text(raw)

    assert "/Users/USER" in cleaned
    assert "C:\\Users\\USER" in cleaned
    assert "USER@DOMAIN" in cleaned
    assert "api_key=REDACTED" in cleaned


def test_extract_critical_sections_prefers_error_context():
    lines = [f"INFO line {i}" for i in range(120)]
    lines[60] = "ERROR connection timeout"
    text = "\n".join(lines)

    result = extract_critical_sections(text, window_size=2, max_lines=20)

    assert "ERROR connection timeout" in result
    assert "INFO line 0" not in result
    assert "INFO line 119" not in result
