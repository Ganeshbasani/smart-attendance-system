"""Unit tests for multi-face preprocessing and tracking (no model weights required)."""

import numpy as np
import pytest

from app.services.multiface import (
    ByteTrackTracker,
    FaceDetection,
    align_face_112,
    cosine_similarity,
    normalize_embedding,
)


def detection(box=(10, 10, 50, 60), score=0.9, quality=70, landmarks=None):
    return FaceDetection(np.array(box), score, landmarks=landmarks, quality=quality)


def test_embedding_is_l2_normalized():
    result = normalize_embedding(np.array([3.0, 4.0], dtype=np.float64))
    assert result.dtype == np.float32
    assert np.linalg.norm(result) == pytest.approx(1.0)
    assert result.tolist() == pytest.approx([0.6, 0.8])


def test_cosine_similarity_is_magnitude_invariant():
    assert cosine_similarity(np.array([2.0, 0.0]), np.array([50.0, 0.0])) == pytest.approx(1.0)
    assert cosine_similarity(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == pytest.approx(0.0)


@pytest.mark.parametrize("vector", [np.array([]), np.array([0.0, 0.0]), np.array([np.nan, 1.0])])
def test_invalid_embeddings_are_rejected(vector):
    with pytest.raises(ValueError):
        normalize_embedding(vector)


def test_similarity_rejects_dimension_mismatch():
    with pytest.raises(ValueError, match="dimensions"):
        cosine_similarity(np.ones(2), np.ones(3))


def test_face_alignment_uses_five_landmarks_and_112_input():
    image = np.zeros((160, 160, 3), dtype=np.uint8)
    points = np.arange(10, dtype=np.float32).reshape(5, 2)
    calls = {}

    def fake_aligner(frame, *, landmark, image_size):
        calls["frame"] = frame
        calls["landmark"] = landmark
        calls["image_size"] = image_size
        return np.zeros((image_size, image_size, 3), dtype=np.uint8)

    aligned = align_face_112(image, points, aligner=fake_aligner)
    assert aligned.shape == (112, 112, 3)
    assert calls["frame"] is image
    np.testing.assert_array_equal(calls["landmark"], points)
    assert calls["image_size"] == 112


def test_face_alignment_rejects_malformed_landmarks():
    with pytest.raises(ValueError, match="five"):
        align_face_112(np.zeros((100, 100, 3), dtype=np.uint8), np.zeros((4, 2)))


def test_tracker_confirms_and_keeps_persistent_ids():
    tracker = ByteTrackTracker(min_hits=2)
    first = tracker.update([detection()])
    assert first == []
    second = tracker.update([detection((11, 10, 51, 60))])
    assert len(second) == 1
    assert second[0].track_id == 1
    assert second[0].confirmed
    assert tracker.update([detection((12, 10, 52, 60))])[0].track_id == 1


def test_low_confidence_detection_recovers_existing_track():
    tracker = ByteTrackTracker(min_hits=2, high_threshold=0.5, low_threshold=0.1)
    tracker.update([detection()])
    result = tracker.update([detection((11, 10, 51, 60), score=0.25)])
    assert len(result) == 1
    assert result[0].track_id == 1
    assert result[0].missed_frames == 0


def test_low_confidence_detection_does_not_create_track():
    tracker = ByteTrackTracker(min_hits=1)
    assert tracker.update([detection(score=0.2)]) == []
    assert tracker.update([detection()])[0].track_id == 1


def test_track_expires_after_configured_occlusion_window():
    tracker = ByteTrackTracker(min_hits=1, max_age=1)
    assert tracker.update([detection()])[0].track_id == 1
    tracker.update([])
    assert tracker.update([]) == []
    assert tracker.update([detection((200, 200, 240, 250))])[0].track_id == 2


def test_recognition_runs_only_on_confirmed_quality_improvement():
    calls = []

    def embedder(frame, landmarks):
        calls.append(1)
        return np.array([3.0, 4.0])

    tracker = ByteTrackTracker(min_hits=2, embedder=embedder, min_quality=20)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    points = np.zeros((5, 2), dtype=np.float32)
    tracker.update([detection(landmarks=points)], frame)
    verified = tracker.update([detection((11, 10, 51, 60), quality=75, landmarks=points)], frame)
    assert calls == [1]
    assert verified[0].recognition_due
    assert np.linalg.norm(verified[0].embedding) == pytest.approx(1.0)

    tracker.update([detection((12, 10, 52, 60), quality=70, landmarks=points)], frame)
    assert calls == [1]


def test_tracker_rejects_invalid_thresholds():
    with pytest.raises(ValueError):
        ByteTrackTracker(high_threshold=0.2, low_threshold=0.3)
