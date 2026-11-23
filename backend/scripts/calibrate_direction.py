#!/usr/bin/env python3
"""
Measure the yaw sign convention of the liveness capture pipeline from logs.

Why this exists
---------------
The head-turn liveness check enforces that the subject turned in the requested
direction. Whether the measured yaw increases or decreases when the subject
turns "left" depends on two stacked conventions that are documented but never
verified against this pipeline:

  1. the capture path mirrors frames (FaceCamera sets react-webcam's
     `mirrored`, which flips the screenshot bytes), and
  2. InsightFace's yaw sign for its pose model.

Guessing the sign would risk rejecting every genuine user, so enforcement
(LIVENESS_REQUIRE_DIRECTION) ships disabled and both directional extents are
logged on every attempt (`yaw_directional` toward the requested direction,
`yaw_directional_opposite` the other way). This tool turns those log lines
into a measured sign recommendation.

Usage (from backend/):
    python -m scripts.calibrate_direction path/to/backend.log
    docker logs <backend> 2>&1 | python -m scripts.calibrate_direction -

Verdict (per attempt: which extent was larger, given real motion)
    requested extent predominantly larger -> keep LIVENESS_DIRECTION_SIGN=1
    opposite extent predominantly larger   -> set LIVENESS_DIRECTION_SIGN=-1
    mixed / too little data               -> no recommendation; collect more

Honesty note: only real capture attempts through this pipeline (mirrored
webcam included) are valid calibration data. Attempts whose motion magnitude
is near zero (subject barely moved) are excluded from the count — they carry
no directional information.
"""

import argparse
import ast
import json
import sys
from typing import Dict, Iterable, List, Optional

METRICS_PREFIX = "Liveness metrics:"


# --------------------------------------------------------------------------- #
# Parsing (pure — unit-testable)
# --------------------------------------------------------------------------- #
def extract_metrics(line: str) -> Optional[Dict]:
    """Pull the liveness metrics dict out of a log line, if this is one."""
    idx = line.find(METRICS_PREFIX)
    if idx < 0:
        return None
    rest = line[idx + len(METRICS_PREFIX):].strip()
    if not rest:
        return None
    # Normal log format: Python dict repr until end of line. Also tolerate a
    # JSON-wrapped line where the message is embedded in a JSON object.
    for candidate in (rest, rest.rstrip("}\"' ")):
        if not candidate:
            continue
        try:
            value = ast.literal_eval(candidate)
            if isinstance(value, dict):
                return value
        except (ValueError, SyntaxError):
            pass
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except (ValueError, json.JSONDecodeError):
            pass
    # Last resort: first balanced-looking {...} substring.
    start, end = rest.find("{"), rest.rfind("}")
    if start >= 0 and end > start:
        try:
            value = ast.literal_eval(rest[start:end + 1])
            if isinstance(value, dict):
                return value
        except (ValueError, SyntaxError):
            pass
    return None


def parse_lines(lines: Iterable[str]) -> List[Dict]:
    records = []
    for line in lines:
        metrics = extract_metrics(line)
        if metrics is not None:
            records.append(metrics)
    return records


# --------------------------------------------------------------------------- #
# Verdict (pure — unit-testable)
# --------------------------------------------------------------------------- #
def summarize(
    records: Iterable[Dict],
    min_attempts: int = 10,
    min_magnitude: float = 3.0,
) -> Dict:
    """
    Decide the direction sign from logged extents.

    Each attempt logs `yaw_directional` (extent toward the requested direction
    under the documented convention) and, since the extent split,
    `yaw_directional_opposite` (extent the other way). If the capture path's
    sign convention matches the documentation, a compliant subject's attempt
    has requested > opposite; if the pipeline is mirrored, it is the other way
    round. Attempts with no meaningful motion in either direction carry no
    directional information and are excluded.
    """
    records = list(records)
    correct = 0
    inverted = 0
    excluded_small = 0
    requested_values = []
    for rec in records:
        requested = rec.get("yaw_directional")
        direction = rec.get("requested_direction")
        if not isinstance(requested, (int, float)) or direction not in ("left", "right"):
            continue
        requested = float(requested)
        opposite = rec.get("yaw_directional_opposite")
        if isinstance(opposite, (int, float)):
            # Current log format: both extents recorded directly.
            opposite = float(opposite)
            if max(requested, opposite) < min_magnitude:
                excluded_small += 1
                continue
            is_correct = requested > opposite
        else:
            # Older logs predate the opposite extent: infer motion from the
            # sweep. Motion with no requested-direction extent means the turn
            # measured the other way round (or the subject turned wrong —
            # either way those attempts cannot confirm the convention).
            sweep = rec.get("yaw_sweep")
            if not isinstance(sweep, (int, float)) or float(sweep) < min_magnitude:
                excluded_small += 1
                continue
            is_correct = requested >= min_magnitude
        requested_values.append(requested)
        if is_correct:
            correct += 1
        else:
            inverted += 1

    attempts = correct + inverted
    pos_fraction = (correct / attempts) if attempts else None

    summary = {
        "records_parsed": len(records),
        "attempts_used": attempts,
        "attempts_excluded_below_magnitude": excluded_small,
        "correct_convention": correct,
        "inverted_convention": inverted,
        "positive_fraction": round(pos_fraction, 3) if pos_fraction is not None else None,
        "mean_requested_extent": (
            round(sum(requested_values) / len(requested_values), 2)
            if requested_values
            else None
        ),
        "min_attempts": min_attempts,
        "recommended_sign": None,
        "recommendation": None,
    }

    if attempts < min_attempts:
        summary["recommendation"] = (
            f"Insufficient data: {attempts} usable attempt(s) < {min_attempts} "
            "required. Collect more real capture attempts through the webcam "
            "flow, then re-run. No sign change recommended."
        )
        return summary

    assert pos_fraction is not None
    if pos_fraction >= 0.75:
        summary["recommended_sign"] = 1
        summary["recommendation"] = (
            "Measured yaw matches the documented convention: keep "
            "LIVENESS_DIRECTION_SIGN=1 (current default) if not already set."
        )
    elif pos_fraction <= 0.25:
        summary["recommended_sign"] = -1
        summary["recommendation"] = (
            "Measured yaw is inverted relative to the documented convention "
            "(consistent with the mirrored capture path): set "
            "LIVENESS_DIRECTION_SIGN=-1 before enabling LIVENESS_REQUIRE_DIRECTION."
        )
    else:
        summary["recommendation"] = (
            "Convention is mixed (neither predominantly correct nor "
            "inverted). Collect more attempts — or check whether more than "
            "one capture path (mirrored and unmirrored) is feeding these logs."
        )
    return summary


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Measure the liveness yaw-direction sign from logged metrics and "
            "recommend LIVENESS_DIRECTION_SIGN. Reads log files, or '-' for stdin."
        )
    )
    parser.add_argument(
        "logs",
        nargs="+",
        help="Log file path(s), or '-' to read stdin",
    )
    parser.add_argument(
        "--min-attempts",
        type=int,
        default=10,
        help="Usable attempts required before any recommendation (default 10)",
    )
    parser.add_argument(
        "--min-magnitude",
        type=float,
        default=3.0,
        help="Degrees below which an attempt carries no directional information",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    return parser


def _iter_lines(paths: List[str]):
    if paths == ["-"]:
        for line in sys.stdin:
            yield line
        return
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    yield line
        except OSError as exc:
            print(f"ERROR: could not read {path}: {exc}", file=sys.stderr)


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    records = parse_lines(_iter_lines(args.logs))

    if not records:
        print(
            "ERROR: no 'Liveness metrics:' lines found. This tool needs real "
            "capture-attempt logs from this pipeline (mirrored webcam included).",
            file=sys.stderr,
        )
        return 2

    summary = summarize(records, min_attempts=args.min_attempts,
                        min_magnitude=args.min_magnitude)

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"Metrics records parsed:   {summary['records_parsed']}")
    print(f"Usable attempts:          {summary['attempts_used']} "
          f"(excluded {summary['attempts_excluded_below_magnitude']} with "
          f"insufficient motion)")
    if summary["positive_fraction"] is not None:
        print(f"Convention matched:       {summary['correct_convention']} / "
              f"{summary['attempts_used']} ({summary['positive_fraction']:.1%})")
        print(f"Inverted:                 {summary['inverted_convention']}")
        print(f"Mean requested extent:    {summary['mean_requested_extent']}")
    print(f"Recommendation:           {summary['recommendation']}")
    if summary["recommended_sign"] is not None:
        print(f"Recommended sign:         LIVENESS_DIRECTION_SIGN={summary['recommended_sign']}")
        print(
            "Reminder: the sign only matters once LIVENESS_REQUIRE_DIRECTION=true; "
            "the sweep-magnitude check is sign-independent."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
