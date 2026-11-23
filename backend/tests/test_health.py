"""Health, readiness, and request-id correlation tests."""

import re

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_returns_ready_when_db_reachable(client):
    """`/ready` must verify DB connectivity, not just process liveness."""
    resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_request_id_generated_when_absent(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    request_id = resp.headers.get("X-Request-ID")
    assert request_id, "response must carry a generated X-Request-ID"
    assert re.fullmatch(r"[0-9a-f]{32}", request_id), request_id


@pytest.mark.asyncio
async def test_request_id_echoed_when_provided(client):
    resp = await client.get("/health", headers={"X-Request-ID": "corr-abc-123"})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == "corr-abc-123"


@pytest.mark.asyncio
async def test_overlong_request_id_is_truncated(client):
    spoofed = "x" * 500
    resp = await client.get("/health", headers={"X-Request-ID": spoofed})
    assert resp.status_code == 200
    assert len(resp.headers.get("X-Request-ID", "")) <= 128


@pytest.mark.asyncio
async def test_security_headers_still_present(client):
    """Regression: request-id middleware must not drop security headers."""
    resp = await client.get("/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
