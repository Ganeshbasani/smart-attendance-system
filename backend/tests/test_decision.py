"""Tests for the deterministic decision engine (AttendX Module 5)."""

from app.services import decision as engine

BASE = dict(
    session_active=True, duplicate=False, liveness_ok=True,
    spoof_suspected=False, confidence=80.0, quality_score=80.0,
    min_confidence=50.0, min_quality=45.0,
)


def test_verified_when_all_signals_good():
    d = engine.evaluate(**BASE)
    assert d.outcome == engine.VERIFIED
    assert "Verified" in d.reason


def test_rejected_without_active_session():
    d = engine.evaluate(**{**BASE, "session_active": False})
    assert d.outcome == engine.REJECTED
    assert "No active" in d.reason


def test_duplicate_detected():
    d = engine.evaluate(**{**BASE, "duplicate": True})
    assert d.outcome == engine.DUPLICATE


def test_spoof_takes_precedence_over_uncertainty():
    # Even a low-confidence frame with a spoof flag must be REJECTED, not
    # softened into REVIEW_REQUIRED.
    d = engine.evaluate(**{**BASE, "spoof_suspected": True, "confidence": 10.0})
    assert d.outcome == engine.REJECTED


def test_liveness_failure_is_rejected():
    d = engine.evaluate(**{**BASE, "liveness_ok": False})
    assert d.outcome == engine.REJECTED


def test_low_confidence_goes_to_review():
    d = engine.evaluate(**{**BASE, "confidence": 30.0})
    assert d.outcome == engine.REVIEW_REQUIRED
    assert d.threshold == 50.0


def test_low_quality_goes_to_review():
    d = engine.evaluate(**{**BASE, "quality_score": 20.0})
    assert d.outcome == engine.REVIEW_REQUIRED


def test_all_outcomes_are_in_vocabulary():
    for outcome in (engine.VERIFIED, engine.REVIEW_REQUIRED, engine.REJECTED,
                    engine.DUPLICATE, engine.MANUAL_OVERRIDE):
        assert outcome in engine.OUTCOMES
