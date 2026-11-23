"""Experimental multi-face detection, tracking, and quality-frame selection.

This service is deliberately separate from the existing single-person kiosk
flow. Track IDs are process-local and short-lived; they must never be treated
as identity. Embeddings are computed only when a confirmed track receives a
new best-quality frame. No video or frame is persisted by this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment


@dataclass
class FaceDetection:
    bbox: np.ndarray
    score: float
    landmarks: Optional[np.ndarray] = None
    quality: float = 0.0
    embedding: Optional[np.ndarray] = None

    def __post_init__(self):
        self.bbox = np.asarray(self.bbox, dtype=np.float32).reshape(4)
        if self.landmarks is not None:
            self.landmarks = np.asarray(self.landmarks, dtype=np.float32).reshape(-1, 2)
        self.score = float(self.score)
        self.quality = float(self.quality)


@dataclass
class TrackedFace:
    track_id: int
    bbox: list[float]
    detection_score: float
    quality: float
    confirmed: bool
    missed_frames: int
    recognition_due: bool
    embedding: Optional[list[float]] = None


@dataclass
class _Track:
    track_id: int
    state: np.ndarray  # cx, cy, width, height, and their velocities
    covariance: np.ndarray
    score: float
    quality: float
    hits: int = 1
    age: int = 1
    missed: int = 0
    best_quality: float = -1.0
    embedding: Optional[np.ndarray] = None

    @property
    def bbox(self) -> np.ndarray:
        cx, cy, width, height = self.state[:4]
        width, height = max(float(width), 1.0), max(float(height), 1.0)
        return np.array([cx - width / 2, cy - height / 2,
                         cx + width / 2, cy + height / 2], dtype=np.float32)


def _bbox_measurement(box: np.ndarray) -> np.ndarray:
    x1, y1, x2, y2 = np.asarray(box, dtype=np.float32)
    width, height = max(x2 - x1, 1.0), max(y2 - y1, 1.0)
    return np.array([(x1 + x2) / 2, (y1 + y2) / 2, width, height], dtype=np.float32)


def _iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)), dtype=np.float32)
    top_left = np.maximum(a[:, None, :2], b[None, :, :2])
    bottom_right = np.minimum(a[:, None, 2:], b[None, :, 2:])
    wh = np.maximum(bottom_right - top_left, 0.0)
    intersection = wh[..., 0] * wh[..., 1]
    area_a = np.maximum(a[:, 2] - a[:, 0], 0) * np.maximum(a[:, 3] - a[:, 1], 0)
    area_b = np.maximum(b[:, 2] - b[:, 0], 0) * np.maximum(b[:, 3] - b[:, 1], 0)
    return intersection / np.maximum(area_a[:, None] + area_b[None, :] - intersection, 1e-6)


class ByteTrackTracker:
    """ByteTrack-style two-stage association with an 8D constant-velocity Kalman filter.

    High-confidence detections associate first. Unmatched existing tracks can
    then recover against low-confidence detections. Only unmatched high-score
    detections create tracks, following ByteTrack's anti-fragmentation rule.
    """

    def __init__(self, high_threshold: float = 0.5, low_threshold: float = 0.1,
                 match_iou: float = 0.25, min_hits: int = 2, max_age: int = 15,
                 min_quality: float = 20.0,
                 embedder: Optional[Callable[[np.ndarray, np.ndarray], np.ndarray]] = None):
        if not 0 <= low_threshold <= high_threshold <= 1:
            raise ValueError("Tracker thresholds must satisfy 0 <= low <= high <= 1")
        if min_hits < 1 or max_age < 0:
            raise ValueError("min_hits must be positive and max_age non-negative")
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.match_iou = match_iou
        self.min_hits = min_hits
        self.max_age = max_age
        self.min_quality = min_quality
        self.embedder = embedder
        self._tracks: dict[int, _Track] = {}
        self._next_id = 1

    @staticmethod
    def _predict(track: _Track) -> None:
        transition = np.eye(8, dtype=np.float32)
        transition[:4, 4:] = np.eye(4, dtype=np.float32)
        noise = np.diag([1, 1, 2, 2, 4, 4, 4, 4]).astype(np.float32)
        track.state = transition @ track.state
        track.state[2:4] = np.maximum(track.state[2:4], 1.0)
        track.covariance = transition @ track.covariance @ transition.T + noise
        track.age += 1
        track.missed += 1

    @staticmethod
    def _correct(track: _Track, detection: FaceDetection) -> None:
        observation = np.zeros((4, 8), dtype=np.float32)
        observation[:, :4] = np.eye(4, dtype=np.float32)
        measurement_noise = np.diag([4, 4, 9, 9]).astype(np.float32)
        z = _bbox_measurement(detection.bbox)
        residual = z - observation @ track.state
        covariance = observation @ track.covariance @ observation.T + measurement_noise
        gain = track.covariance @ observation.T @ np.linalg.inv(covariance)
        track.state = track.state + gain @ residual
        track.covariance = (np.eye(8, dtype=np.float32) - gain @ observation) @ track.covariance
        track.score = detection.score
        track.quality = detection.quality
        track.hits += 1
        track.missed = 0

    def _associate(self, track_ids: list[int], detection_indices: list[int],
                   detections: list[FaceDetection]) -> dict[int, int]:
        if not track_ids or not detection_indices:
            return {}
        track_boxes = np.stack([self._tracks[i].bbox for i in track_ids])
        det_boxes = np.stack([detections[i].bbox for i in detection_indices])
        ious = _iou_matrix(track_boxes, det_boxes)
        rows, cols = linear_sum_assignment(1.0 - ious)
        matches = {}
        for row, col in zip(rows, cols):
            if ious[row, col] < self.match_iou:
                continue
            tid, didx = track_ids[row], detection_indices[col]
            self._correct(self._tracks[tid], detections[didx])
            matches[tid] = didx
        return matches

    def update(self, detections: list[FaceDetection], frame: Optional[np.ndarray] = None) -> list[TrackedFace]:
        high = [i for i, d in enumerate(detections) if d.score >= self.high_threshold]
        low = [i for i, d in enumerate(detections) if self.low_threshold <= d.score < self.high_threshold]
        for track in self._tracks.values():
            self._predict(track)

        ids = list(self._tracks)
        first_matches = self._associate(ids, high, detections)
        remaining_tracks = [tid for tid in ids if tid not in first_matches]
        second_matches = self._associate(remaining_tracks, low, detections)
        matches = {**first_matches, **second_matches}
        matched_dets = set(matches.values())

        # Best-frame selection happens only for confirmed tracks and at most
        # once per quality improvement. A caller can then match this embedding
        # against its already-authorized room/session gallery.
        for tid, didx in matches.items():
            track = self._tracks[tid]
            detection = detections[didx]
            if (track.hits >= self.min_hits and detection.quality >= self.min_quality
                    and detection.quality > track.best_quality):
                track.best_quality = detection.quality
                if self.embedder is not None and frame is not None and detection.landmarks is not None:
                    track.embedding = normalize_embedding(self.embedder(frame, detection.landmarks))

        for i in high:
            if i in matched_dets:
                continue
            detection = detections[i]
            measurement = _bbox_measurement(detection.bbox)
            state = np.zeros(8, dtype=np.float32)
            state[:4] = measurement
            self._tracks[self._next_id] = _Track(
                track_id=self._next_id, state=state,
                covariance=np.diag([10, 10, 10, 10, 100, 100, 100, 100]).astype(np.float32),
                score=detection.score, quality=detection.quality,
            )
            self._next_id += 1

        stale = [tid for tid, track in self._tracks.items() if track.missed > self.max_age]
        for tid in stale:
            del self._tracks[tid]

        output = []
        for track in self._tracks.values():
            if track.hits < self.min_hits:
                continue
            # Consume the selected embedding after exposing it once; later
            # unchanged/poorer frames do not trigger repeated recognition.
            embedding = track.embedding
            track.embedding = None
            output.append(TrackedFace(
                track_id=track.track_id, bbox=track.bbox.tolist(),
                detection_score=track.score, quality=track.quality,
                confirmed=True, missed_frames=track.missed,
                recognition_due=embedding is not None,
                embedding=embedding.tolist() if embedding is not None else None,
            ))
        return output

    def reset(self) -> None:
        self._tracks.clear()


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
    if vector.size == 0 or not np.all(np.isfinite(vector)):
        raise ValueError("Embedding must be a non-empty finite vector")
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12:
        raise ValueError("Embedding norm must be greater than zero")
    return vector / norm


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    a = normalize_embedding(left)
    b = normalize_embedding(right)
    if a.shape != b.shape:
        raise ValueError("Embedding dimensions must match")
    return float(np.clip(a @ b, -1.0, 1.0))


def align_face_112(frame: np.ndarray, landmarks: np.ndarray,
                   aligner: Optional[Callable] = None) -> np.ndarray:
    """Align a BGR face crop using five landmarks to InsightFace's 112px input."""
    if frame is None or not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("frame must be a three-channel BGR image")
    points = np.asarray(landmarks, dtype=np.float32)
    if points.shape != (5, 2) or not np.all(np.isfinite(points)):
        raise ValueError("alignment requires five finite 2D landmarks")
    if aligner is None:
        from insightface.utils import face_align
        aligner = face_align.norm_crop
    aligned = aligner(frame, landmark=points, image_size=112)
    if not isinstance(aligned, np.ndarray) or aligned.shape != (112, 112, 3):
        raise ValueError("face aligner must return a 112x112 three-channel image")
    return aligned


def face_quality(frame: np.ndarray, bbox: np.ndarray, min_face_px: int = 50) -> tuple[float, dict]:
    """Return a simple capture-quality score; this is not identity confidence."""
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = np.asarray(bbox, dtype=np.int32)
    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(width, x2), min(height, y2)
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return 0.0, {"face_size_px": 0, "sharpness": 0.0, "brightness": 0.0}
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    face_size = min(crop.shape[:2])
    size_score = min(face_size / max(min_face_px, 1), 1.0) * 100.0
    sharp_score = min(sharpness / 100.0, 1.0) * 100.0
    light_score = max(0.0, 100.0 - abs(brightness - 127.5) * (100.0 / 127.5))
    score = round(size_score * 0.35 + sharp_score * 0.4 + light_score * 0.25, 1)
    return score, {"face_size_px": int(face_size), "sharpness": round(sharpness, 2),
                   "brightness": round(brightness, 2)}


class InsightFaceDetectionBackend:
    """SCRFD detector-only path plus ArcFace embedding on demand (BGR frames)."""

    def __init__(self, face_service, min_face_px: int = 50):
        self.face_service = face_service
        self.min_face_px = min_face_px

    def detect(self, frame: np.ndarray) -> list[FaceDetection]:
        app = self.face_service.app
        boxes, landmarks = app.det_model.detect(frame, max_num=0)
        if boxes is None or len(boxes) == 0:
            return []
        found = []
        for i, row in enumerate(boxes):
            bbox, score = row[:4], float(row[4])
            points = landmarks[i] if landmarks is not None and i < len(landmarks) else None
            quality, metrics = face_quality(frame, bbox, self.min_face_px)
            if metrics["face_size_px"] < self.min_face_px:
                continue
            found.append(FaceDetection(bbox=bbox, score=score,
                                       landmarks=points, quality=quality))
        return found

    def embed(self, frame: np.ndarray, landmarks: np.ndarray) -> np.ndarray:
        app = self.face_service.app
        aligned_bgr = align_face_112(frame, landmarks)
        raw = app.models["recognition"].get_feat(aligned_bgr).reshape(-1)
        return normalize_embedding(raw)


class MultiFacePipeline:
    """Single-frame API for a local scanner; owns no camera or network stream."""

    def __init__(self, detector: InsightFaceDetectionBackend,
                 tracker: Optional[ByteTrackTracker] = None):
        self.detector = detector
        self.tracker = tracker or ByteTrackTracker(embedder=detector.embed)

    def process_frame(self, frame: np.ndarray) -> list[TrackedFace]:
        if frame is None or not isinstance(frame, np.ndarray) or frame.ndim != 3:
            raise ValueError("frame must be a BGR image array")
        detections = self.detector.detect(frame)
        return self.tracker.update(detections, frame)
