"""
Operator tooling: threshold benchmarking and direction-sign calibration.

Both scripts are deliberately unable to invent numbers — the benchmark refuses
to evaluate without a labeled dataset, and the calibrator refuses to recommend
a sign without enough real attempts. These tests pin down that behaviour plus
the pure scoring/verdict math.

No InsightFace weights are loaded: the benchmark's model path is only reached
through load_samples(), which these tests do not call with real images.
"""

import numpy as np
import pytest

from scripts.benchmark_thresholds import (
    equal_error_rate,
    main as benchmark_main,
    pair_scores,
    sweep_thresholds,
)
from scripts.calibrate_direction import (
    extract_metrics,
    main as calibrate_main,
    parse_lines,
    summarize,
)


# ── pair_scores ───────────────────────────────────────────────────────────────

def test_pair_scores_splits_genuine_and_impostor():
    a1 = np.array([1.0, 0.0])
    a2 = np.array([1.0, 0.0])   # same identity, identical direction
    b1 = np.array([0.0, 1.0])   # different identity, orthogonal

    genuine, impostor = pair_scores([("alice", a1), ("alice", a2), ("bob", b1)])

    assert len(genuine) == 1          # alice-alice
    assert len(impostor) == 2         # alice-bob x2
    assert genuine[0] == pytest.approx(1.0)
    assert all(s == pytest.approx(0.0) for s in impostor)


def test_pair_scores_normalizes_unnormalized_inputs():
    """Cosine similarity must not depend on vector magnitude."""
    v = np.array([3.0, 0.0])
    w = np.array([7.0, 0.0])
    genuine, _ = pair_scores([("a", v), ("a", w)])
    assert genuine[0] == pytest.approx(1.0)


def test_pair_scores_handles_too_few_samples():
    assert pair_scores([]) == ([], [])
    assert pair_scores([("only", np.array([1.0, 0.0]))]) == ([], [])


# ── sweep / EER ───────────────────────────────────────────────────────────────

def test_sweep_thresholds_far_frr():
    genuine = [0.9, 0.8, 0.7]
    impostor = [0.3, 0.2, 0.1]

    rows = sweep_thresholds(genuine, impostor, [0.5, 0.95])

    # At 0.5: all impostors rejected (FAR 0), all genuine accepted (FRR 0).
    assert rows[0]["far"] == 0.0
    assert rows[0]["frr"] == 0.0
    # At 0.95: every pair rejected — impostors all below (FAR 0),
    # genuine all below threshold (FRR 1.0).
    assert rows[1]["far"] == 0.0
    assert rows[1]["frr"] == 1.0


def test_sweep_far_at_low_threshold():
    """Below every impostor score, FAR is 1.0 — the false-accept extreme."""
    rows = sweep_thresholds(genuine=[0.9], impostor=[0.6, 0.7], thresholds=[0.1])
    assert rows[0]["far"] == 1.0
    assert rows[0]["frr"] == 0.0


def test_sweep_marks_missing_side_as_nan():
    rows = sweep_thresholds(genuine=[], impostor=[0.5], thresholds=[0.3])
    assert not np.isnan(rows[0]["far"])
    assert np.isnan(rows[0]["frr"])


def test_equal_error_rate_picks_closest_crossing():
    rows = [
        {"threshold": 0.3, "far": 0.10, "frr": 0.00},
        {"threshold": 0.4, "far": 0.04, "frr": 0.03},   # |diff| = 0.01 (best)
        {"threshold": 0.5, "far": 0.00, "frr": 0.20},
    ]
    eer = equal_error_rate(rows)
    assert eer["threshold"] == 0.4
    assert eer["eer"] == pytest.approx(0.035)


def test_equal_error_rate_none_when_one_side_missing():
    rows = [{"threshold": 0.3, "far": float("nan"), "frr": 0.1}]
    assert equal_error_rate(rows) is None


# ── benchmark CLI refuses to invent numbers ───────────────────────────────────

def test_benchmark_fails_on_missing_dataset(tmp_path, capsys):
    rc = benchmark_main(["--dataset", str(tmp_path / "nope")])
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_benchmark_fails_on_dataset_without_identities(tmp_path, capsys):
    empty = tmp_path / "dataset"
    empty.mkdir()
    rc = benchmark_main(["--dataset", str(empty)])
    assert rc == 2
    assert "identity subdirectories" in capsys.readouterr().err


# ── direction calibration: parsing ────────────────────────────────────────────

def test_extract_metrics_from_typical_log_line():
    line = (
        "2026-01-05 10:00:00,123 | INFO     | abc123 | "
        "smart_attendance.liveness | Liveness metrics: "
        "{'frames_submitted': 8, 'yaw_sweep': 21.5, 'yaw_directional': 19.0, "
        "'yaw_directional_opposite': 2.5, 'requested_direction': 'left'}"
    )
    metrics = extract_metrics(line)
    assert metrics is not None
    assert metrics["yaw_directional"] == 19.0
    assert metrics["requested_direction"] == "left"


def test_extract_metrics_returns_none_for_other_lines():
    assert extract_metrics("INFO | something else happened") is None
    assert extract_metrics("Liveness metrics: ") is None


def test_parse_lines_filters_to_metrics_only():
    lines = [
        "startup line",
        "Liveness metrics: {'yaw_directional': 5.0, 'yaw_sweep': 6.0, "
        "'requested_direction': 'right'}",
        "unrelated",
    ]
    assert len(parse_lines(lines)) == 1


# ── direction calibration: verdict ────────────────────────────────────────────

def _records(n, correct, inverted, min_motion=10.0):
    """Build n records: `correct` matching the documented convention."""
    recs = []
    for i in range(n):
        if i < correct:
            recs.append(
                {"yaw_directional": min_motion + 10.0,
                 "yaw_directional_opposite": 1.0,
                 "yaw_sweep": min_motion + 11.0,
                 "requested_direction": "left"}
            )
        elif i < correct + inverted:
            recs.append(
                {"yaw_directional": 1.0,
                 "yaw_directional_opposite": min_motion + 10.0,
                 "yaw_sweep": min_motion + 11.0,
                 "requested_direction": "left"}
            )
        else:
            recs.append(
                {"yaw_directional": 0.5,
                 "yaw_directional_opposite": 0.4,
                 "yaw_sweep": 1.0,   # no real motion -> excluded
                 "requested_direction": "left"}
            )
    return recs


def test_calibrate_recommends_plus_one_when_convention_matches():
    summary = summarize(_records(12, correct=12, inverted=0), min_attempts=10)
    assert summary["recommended_sign"] == 1
    assert summary["attempts_used"] == 12


def test_calibrate_recommends_minus_one_when_inverted():
    summary = summarize(_records(12, correct=0, inverted=12), min_attempts=10)
    assert summary["recommended_sign"] == -1
    assert summary["inverted_convention"] == 12


def test_calibrate_no_recommendation_below_min_attempts():
    summary = summarize(_records(4, correct=4, inverted=0), min_attempts=10)
    assert summary["recommended_sign"] is None
    assert "Insufficient data" in summary["recommendation"]


def test_calibrate_no_recommendation_when_mixed():
    summary = summarize(_records(12, correct=6, inverted=6), min_attempts=10)
    assert summary["recommended_sign"] is None
    assert "mixed" in summary["recommendation"]


def test_calibrate_excludes_low_motion_attempts():
    """Attempts with no real motion carry no directional information."""
    summary = summarize(_records(12, correct=10, inverted=0), min_attempts=5)
    assert summary["attempts_used"] == 10
    assert summary["attempts_excluded_below_magnitude"] == 2


def test_calibrate_falls_back_to_sweep_for_old_logs():
    """Logs from before the opposite-extent field: infer from yaw_sweep."""
    old_format = [
        {"yaw_directional": 20.0, "yaw_sweep": 22.0, "requested_direction": "left"}
        for _ in range(6)
    ] + [
        # Motion present but none in the requested direction -> inverted.
        {"yaw_directional": 0.5, "yaw_sweep": 18.0, "requested_direction": "left"}
        for _ in range(6)
    ]
    summary = summarize(old_format, min_attempts=10)
    assert summary["correct_convention"] == 6
    assert summary["inverted_convention"] == 6
    assert summary["recommended_sign"] is None


def test_calibrate_cli_refuses_logs_without_metrics(tmp_path, capsys):
    log = tmp_path / "app.log"
    log.write_text("nothing relevant here\n", encoding="utf-8")
    rc = calibrate_main([str(log)])
    assert rc == 2
    assert "no 'Liveness metrics:' lines" in capsys.readouterr().err
