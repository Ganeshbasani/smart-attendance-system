from services.risk_engine import runway, risk_state


def test_runway_exact_requirement():
    r = runway(attended=18, conducted=20, remaining=7, threshold=75)
    assert r["required_future"] == 3
    assert r["safe_misses"] == 4
    assert r["recoverable"] is True


def test_runway_recovery_impossible():
    r = runway(attended=10, conducted=20, remaining=6, threshold=75)
    assert r["required_future"] == 6
    assert r["safe_misses"] == 0
    assert r["recoverable"] is False


def test_critical_risk():
    risk = risk_state(58, -10, 4, 4, True, 61, 75, 1.2)
    assert risk["state"] == "Critical"
    assert risk["signals"]


def test_safe_risk():
    risk = risk_state(90, 1.5, 0, 10, True, 88, 75, 1.0)
    assert risk["state"] == "Safe"
