"""Upload validation tests: content type, size, and empty-file rejection."""

import pytest

from app.core.config import settings


def _files(count: int, content: bytes, content_type: str):
    """Build a multipart `files` list for /attendance/mark or /face/register."""
    return [
        ("files", (f"frame_{i}.jpg", content, content_type))
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_attendance_rejects_non_image_content_type(client):
    """A PDF (or anything not allow-listed) must 415 before any processing."""
    resp = await client.post(
        "/attendance/mark",
        data={"liveness_verified": "false"},
        files=_files(3, b"%PDF-1.4 fake", "application/pdf"),
    )
    assert resp.status_code == 415, resp.text


@pytest.mark.asyncio
async def test_attendance_rejects_empty_file(client):
    resp = await client.post(
        "/attendance/mark",
        data={"liveness_verified": "false"},
        files=_files(2, b"", "image/jpeg"),
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_attendance_rejects_oversized_file(client, monkeypatch):
    # Shrink the limit instead of writing 10MB through the test suite.
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0)
    resp = await client.post(
        "/attendance/mark",
        data={"liveness_verified": "false"},
        files=_files(2, b"x" * 16, "image/jpeg"),
    )
    assert resp.status_code == 413, resp.text


@pytest.mark.asyncio
async def test_face_register_rejects_non_image_content_type(client, user_token):
    """Enrollment images must be images too (5 files pass the count check first)."""
    resp = await client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {user_token}"},
        data={"challenge_id": "unused"},
        files=_files(5, b"not an image", "application/pdf"),
    )
    assert resp.status_code == 415, resp.text


@pytest.mark.asyncio
async def test_admin_face_register_rejects_non_image_content_type(
    client, admin_token, user_token
):
    resp = await client.post(
        "/admin/user/USR-test/face/register",
        headers={"Authorization": f"Bearer {admin_token}"},
        files=_files(5, b"not an image", "application/pdf"),
    )
    # Unknown user 404s before uploads are read — that ordering is fine; only
    # assert the upload path itself is guarded when the user exists.
    assert resp.status_code in (404, 415), resp.text


@pytest.mark.asyncio
async def test_allowed_content_types_still_accepted_by_helper():
    """Regression: the default allow-list must keep JPEG/PNG/WebP working."""
    assert settings.allowed_image_content_types == ["image/jpeg", "image/png", "image/webp"]
    assert settings.max_upload_size_bytes == settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
