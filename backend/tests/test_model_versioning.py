"""
Model-version consistency of the face gallery.

The gallery must only ever contain embeddings computed with the currently
configured ArcFace pack: mixing packs puts vectors from different spaces into
one cosine search, producing confident-but-wrong matches. These tests cover
the cache filter (model + dimension), the admin model-status report, and the
honesty of the legacy single-image "liveness" response.

Model calls are stubbed — no InsightFace weights are loaded.
"""

from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from app.core.config import settings
from app.models import FaceEmbedding, User
from app.services.face_recognition import face_service


def _unit_vector(dim_index: int, size: int = 512) -> np.ndarray:
    v = np.zeros(size, dtype=np.float32)
    v[dim_index] = 1.0
    return v


def _add_embedding(
    db,
    unique_id: str,
    email: str,
    emb: np.ndarray,
    model: str = "buffalo_l",
) -> User:
    user = User(
        email=email,
        password="hashed",
        full_name=unique_id,
        unique_id=unique_id,
        role="user",
        is_active=True,
        face_registered=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    arr = np.asarray(emb, dtype=np.float32).reshape(1, -1)
    db.add(
        FaceEmbedding(
            user_id=user.id,
            embeddings=arr.tobytes(),
            count=1,
            dim=int(arr.shape[1]),
            model=model,
        )
    )
    db.commit()
    return user


@pytest.fixture(autouse=True)
def _fresh_cache():
    face_service.invalidate_cache()
    yield
    face_service.invalidate_cache()


# ── Cache filtering ───────────────────────────────────────────────────────────

def test_cache_excludes_rows_from_other_model_packs(db_session):
    """A row computed with a different pack must never enter the gallery."""
    _add_embedding(db_session, "USR_CUR", "cur@test.com", _unit_vector(0))
    _add_embedding(
        db_session, "USR_OLD", "old@test.com", _unit_vector(1), model="arcface_w600k"
    )
    face_service._refresh_cache(db_session)
    assert face_service._cache_labels == ["USR_CUR"]


def test_cache_excludes_rows_with_mismatched_dimension(db_session):
    """
    Same pack but a corrupt width: the majority dimension wins and the odd row
    is kept out (a mixed-width vstack would otherwise kill recognition
    entirely).
    """
    _add_embedding(db_session, "USR_OK1", "ok1@test.com", _unit_vector(0, size=512))
    _add_embedding(db_session, "USR_OK2", "ok2@test.com", _unit_vector(1, size=512))
    _add_embedding(db_session, "USR_ODD", "odd@test.com", _unit_vector(2, size=256))
    face_service._refresh_cache(db_session)
    assert face_service._cache_labels == ["USR_OK1", "USR_OK2"]
    assert face_service._cache_embeddings.shape == (2, 512)


def test_cache_ignores_changes_to_stale_rows(db_session):
    """
    The invalidation signature is computed over the filtered set: updating a
    stale row must not force a rebuild of a gallery it is not part of (the
    unfiltered signature would have changed with max(updated_at)).
    """
    from app.core.time_utils import utc_now_naive

    _add_embedding(db_session, "USR_CUR", "cur@test.com", _unit_vector(0))
    _add_embedding(
        db_session, "USR_OLD", "old@test.com", _unit_vector(1), model="arcface_w600k"
    )
    face_service._refresh_cache(db_session)
    signature_before = face_service._cache_signature

    stale_row = db_session.query(FaceEmbedding).filter(
        FaceEmbedding.model == "arcface_w600k"
    ).first()
    stale_row.updated_at = utc_now_naive()
    db_session.commit()

    face_service._refresh_cache(db_session)
    assert face_service._cache_signature == signature_before


# ── model_status ──────────────────────────────────────────────────────────────

def test_model_status_counts_matching_and_stale_rows(db_session):
    _add_embedding(db_session, "USR_CUR", "cur@test.com", _unit_vector(0))
    _add_embedding(
        db_session, "USR_OLD1", "old1@test.com", _unit_vector(1), model="arcface_w600k"
    )
    _add_embedding(
        db_session, "USR_OLD2", "old2@test.com", _unit_vector(2), model="arcface_w600k"
    )

    status = face_service.model_status(db_session)

    assert status["configured_model"] == settings.FACE_MODEL_PACK
    assert status["total_embedding_rows"] == 3
    assert status["matching_rows"] == 1
    assert status["stale_rows"] == 2
    assert status["by_model"][settings.FACE_MODEL_PACK] == 1
    assert status["by_model"]["arcface_w600k"] == 2
    assert {u["unique_id"] for u in status["stale_users"]} == {"USR_OLD1", "USR_OLD2"}
    assert all(u["model"] == "arcface_w600k" for u in status["stale_users"])
    assert status["gallery_usable"] is True


def test_model_status_reports_unusable_gallery_when_all_stale(db_session):
    _add_embedding(
        db_session, "USR_OLD", "old@test.com", _unit_vector(1), model="arcface_w600k"
    )
    status = face_service.model_status(db_session)
    assert status["matching_rows"] == 0
    assert status["gallery_usable"] is False


def test_model_status_empty_gallery(db_session):
    status = face_service.model_status(db_session)
    assert status["total_embedding_rows"] == 0
    assert status["stale_users"] == []
    assert status["gallery_usable"] is False
    assert status["thresholds"]["match"] == settings.FACE_MATCH_THRESHOLD


# ── Admin endpoint ────────────────────────────────────────────────────────────

async def test_model_status_endpoint_requires_admin(client, user_token):
    resp = await client.get(
        "/admin/face/model-status",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


async def test_model_status_endpoint_for_admin(client, admin_token):
    resp = await client.get(
        "/admin/face/model-status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured_model"] == settings.FACE_MODEL_PACK
    assert "matching_rows" in body
    assert "stale_users" in body
    assert body["thresholds"]["duplicate"] == settings.FACE_DUPLICATE_THRESHOLD


# ── Honest legacy liveness response ───────────────────────────────────────────

def test_check_image_liveness_reports_unmeasured_spoof_probability(tmp_path):
    """
    Face presence is not anti-spoofing: the response must not claim a spoof
    probability it never computed.
    """
    fake_face = SimpleNamespace(det_score=0.93)
    with patch.object(
        face_service, "_detect_primary_face", return_value=(fake_face, None)
    ):
        result = face_service.check_image_liveness("unused.jpg")

    assert result["is_live"] is True
    assert result["spoof_probability"] is None
    assert result["anti_spoofing"] is False
    assert result["method"] == "face_presence_only"
    assert "cannot detect a photo" in result["note"]


def test_check_image_liveness_without_face_is_not_called_a_spoof():
    with patch.object(
        face_service, "_detect_primary_face", return_value=(None, None)
    ):
        result = face_service.check_image_liveness("unused.jpg")

    assert result["is_live"] is False
    assert result["spoof_probability"] is None
    assert result["anti_spoofing"] is False
    assert result["checks_passed"] == {"face_present": False}
