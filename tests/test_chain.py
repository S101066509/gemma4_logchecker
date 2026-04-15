from app.chain import _calibrate_confidence
from app.schemas import DiagnosticReport


def _report(confidence: float, related_files: list[str]) -> DiagnosticReport:
    return DiagnosticReport(
        severity="Medium",
        root_cause="x",
        suggested_fix="y",
        related_files=related_files,
        confidence=confidence,
    )


def test_calibrate_confidence_low_evidence_caps_at_0_70():
    report = _report(confidence=0.95, related_files=[])
    calibrated = _calibrate_confidence(report, log_text="你是誰", has_image=False)
    assert calibrated.confidence == 0.70


def test_calibrate_confidence_no_related_files_caps_at_0_85():
    report = _report(confidence=0.95, related_files=[])
    calibrated = _calibrate_confidence(
        report,
        log_text="ERROR database failed with traceback details",
        has_image=True,
    )
    assert calibrated.confidence == 0.85


def test_calibrate_confidence_keeps_high_confidence_when_evidence_is_strong():
    report = _report(confidence=0.95, related_files=["db.py"])
    calibrated = _calibrate_confidence(
        report,
        log_text="CRITICAL Traceback: connection refused in db.py line 42",
        has_image=True,
    )
    assert calibrated.confidence == 0.95
