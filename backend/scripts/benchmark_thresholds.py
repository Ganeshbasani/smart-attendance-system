#!/usr/bin/env python3
"""
Measure FAR / FRR / EER of the face-matching thresholds on labeled photos.

Why this exists
---------------
FACE_MATCH_THRESHOLD (0.42) and FACE_DUPLICATE_THRESHOLD (0.50) are described
as "tuned", but the repository contains no labeled dataset, so nothing here
can state a false-accept or false-reject rate from first principles — and this
tool deliberately prints NO accuracy figures until an operator points it at
real, labeled images. Every number it reports is computed from those images.

Usage (from backend/):
    python -m scripts.benchmark_thresholds --dataset path/to/benchmark

Dataset layout — one subdirectory per identity, images inside:
    benchmark/
      alice/  img1.jpg img2.jpg ...
      bob/    img1.jpg ...

What it reports
    * FAR (false accept rate): impostor pairs scoring >= threshold
    * FRR (false reject rate): genuine pairs scoring <  threshold
    * the equal-error-rate (EER) point on this data
    * how the currently configured thresholds score on this data

The sweep is informational: it does not change any configuration. Pick a
threshold from your own measured trade-off and set it explicitly.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


# --------------------------------------------------------------------------- #
# Pure scoring logic (no model, no I/O — unit-testable)
# --------------------------------------------------------------------------- #
def pair_scores(
    samples: Sequence[Tuple[str, np.ndarray]]
) -> Tuple[List[float], List[float]]:
    """
    Cosine similarity for every unordered pair, split genuine vs impostor.

    `samples` is a sequence of (identity_label, embedding). Embeddings are
    L2-normalized here so the dot product is the cosine similarity regardless
    of how the caller produced them.
    """
    if len(samples) < 2:
        return [], []

    labels = np.array([label for label, _ in samples])
    emb = np.stack([np.asarray(v, dtype=np.float64).ravel() for _, v in samples])
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    emb = emb / norms

    sims = emb @ emb.T
    iu = np.triu_indices(len(samples), k=1)
    scores = sims[iu]
    same = labels[iu[0]] == labels[iu[1]]
    return scores[same].tolist(), scores[~same].tolist()


def sweep_thresholds(
    genuine: Sequence[float],
    impostor: Sequence[float],
    thresholds: Sequence[float],
) -> List[Dict]:
    """FAR/FRR at each threshold. FAR = impostors accepted; FRR = genuine rejected."""
    rows = []
    for t in thresholds:
        far = (
            float(np.mean([s >= t for s in impostor])) if impostor else float("nan")
        )
        frr = float(np.mean([s < t for s in genuine])) if genuine else float("nan")
        rows.append({"threshold": round(float(t), 4), "far": far, "frr": frr})
    return rows


def equal_error_rate(rows: Sequence[Dict]) -> Optional[Dict]:
    """Row where |FAR - FRR| is smallest — the EER operating point on this data."""
    usable = [r for r in rows if not np.isnan(r["far"]) and not np.isnan(r["frr"])]
    if not usable:
        return None
    best = min(usable, key=lambda r: abs(r["far"] - r["frr"]))
    return {
        "threshold": best["threshold"],
        "far": best["far"],
        "frr": best["frr"],
        "eer": (best["far"] + best["frr"]) / 2.0,
    }


# --------------------------------------------------------------------------- #
# Dataset loading (uses the real model; operator-run only)
# --------------------------------------------------------------------------- #
def load_samples(dataset_dir: Path) -> Tuple[List[Tuple[str, np.ndarray]], Dict]:
    """
    Encode every image under dataset_dir/<identity>/**.

    Returns (samples, stats). Images with no detectable face are skipped and
    counted — a dataset where the model encodes almost nothing is reported as
    such rather than silently shrinking the evaluation.
    """
    from app.services.face_recognition import face_service

    identity_dirs = sorted(
        d for d in dataset_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
    )
    if not identity_dirs:
        raise ValueError(
            f"No identity subdirectories found in {dataset_dir}. Expected "
            f"{dataset_dir}/<identity>/*.jpg — one folder per person."
        )

    samples: List[Tuple[str, np.ndarray]] = []
    stats = {
        "identities": len(identity_dirs),
        "images_seen": 0,
        "images_encoded": 0,
        "images_failed": 0,
        "per_identity": {},
    }
    for identity_dir in identity_dirs:
        encoded_here = 0
        images = sorted(
            p
            for p in identity_dir.rglob("*")
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        )
        for image_path in images:
            stats["images_seen"] += 1
            emb = face_service.get_embedding(str(image_path))
            if emb is None:
                stats["images_failed"] += 1
                print(f"  ! no face encoded: {image_path}", file=sys.stderr)
                continue
            samples.append((identity_dir.name, emb))
            encoded_here += 1
            stats["images_encoded"] += 1
        stats["per_identity"][identity_dir.name] = encoded_here
        if encoded_here < 2:
            print(
                f"  ! identity '{identity_dir.name}' has {encoded_here} usable "
                f"image(s); needs >= 2 to contribute genuine pairs",
                file=sys.stderr,
            )
    return samples, stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Measure FAR/FRR/EER of face-matching thresholds on a labeled "
            "dataset. Prints nothing until real images are supplied."
        )
    )
    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Directory with one subfolder of images per identity",
    )
    parser.add_argument("--min-threshold", type=float, default=0.20)
    parser.add_argument("--max-threshold", type=float, default=0.70)
    parser.add_argument("--step", type=float, default=0.01)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a table",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.dataset.is_dir():
        print(f"ERROR: dataset directory not found: {args.dataset}", file=sys.stderr)
        return 2

    from app.core.config import settings

    try:
        samples, stats = load_samples(args.dataset)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    genuine, impostor = pair_scores(samples)
    if not genuine or not impostor:
        print(
            "ERROR: cannot evaluate — need at least one genuine pair (an "
            "identity with >= 2 encoded images) and one impostor pair (>= 2 "
            "distinct identities). "
            f"genuine_pairs={len(genuine)} impostor_pairs={len(impostor)}",
            file=sys.stderr,
        )
        return 2

    steps = int(round((args.max_threshold - args.min_threshold) / args.step)) + 1
    thresholds = [args.min_threshold + i * args.step for i in range(max(steps, 1))]
    # Always evaluate the configured operating points too.
    for configured in (settings.FACE_MATCH_THRESHOLD, settings.FACE_DUPLICATE_THRESHOLD):
        if configured not in thresholds:
            thresholds.append(configured)
    thresholds = sorted(thresholds)

    rows = sweep_thresholds(genuine, impostor, thresholds)
    eer = equal_error_rate(rows)

    result = {
        "dataset": str(args.dataset),
        "stats": stats,
        "genuine_pairs": len(genuine),
        "impostor_pairs": len(impostor),
        "configured": {
            "face_match_threshold": settings.FACE_MATCH_THRESHOLD,
            "face_duplicate_threshold": settings.FACE_DUPLICATE_THRESHOLD,
        },
        "rows": rows,
        "eer": eer,
        "disclaimer": (
            "Measured only on the supplied dataset; not a general accuracy "
            "claim. Re-run with a representative sample of your deployment."
        ),
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Dataset:            {args.dataset}")
    print(
        f"Identities:         {stats['identities']}  "
        f"(images seen {stats['images_seen']}, encoded {stats['images_encoded']}, "
        f"failed {stats['images_failed']})"
    )
    print(f"Genuine pairs:      {len(genuine)}")
    print(f"Impostor pairs:     {len(impostor)}")
    print()
    print("Threshold   FAR        FRR")
    for row in rows:
        marker = ""
        if row["threshold"] == settings.FACE_MATCH_THRESHOLD:
            marker = "  <- FACE_MATCH_THRESHOLD"
        elif row["threshold"] == settings.FACE_DUPLICATE_THRESHOLD:
            marker = "  <- FACE_DUPLICATE_THRESHOLD"
        far = "n/a" if np.isnan(row["far"]) else f"{row['far']:.4f}"
        frr = "n/a" if np.isnan(row["frr"]) else f"{row['frr']:.4f}"
        print(f"{row['threshold']:<11.3f} {far:<10} {frr}{marker}")
    print()
    if eer:
        print(
            f"Equal error rate:   EER={eer['eer']:.4f} at threshold "
            f"{eer['threshold']:.3f} (FAR={eer['far']:.4f}, FRR={eer['frr']:.4f})"
        )
    print(
        "Note: measured only on the supplied dataset — not a general accuracy "
        "claim. Re-run with a representative sample of your deployment."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
