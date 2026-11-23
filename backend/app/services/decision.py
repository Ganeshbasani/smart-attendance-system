"""
Central, deterministic attendance decision engine (AttendX Module 5).

Every session-based verification passes through ``evaluate``. It is a pure
function: given the recorded signals it returns one outcome and a reason that
is safe to show to a human reviewer. Thresholds arrive as parameters so they
are env-configurable and easy to test — no hidden constants.

Outcomes
--------
VERIFIED          only outcome that is auto-accepted.
REVIEW_REQUIRED   uncertain match / low-quality frame — a human decides.
REJECTED          spoof suspected, liveness failed, or no active session.
DUPLICATE         this student already has a record in this session.
MANUAL_OVERRIDE   produced only by an explicit, reasoned teacher action.

This engine makes no accuracy claims. It applies policy to the signals it is
given; the quality of those signals depends on the CV models that produced
them (see docs/AI_MODELS.md).
"""

from dataclasses import dataclass
from typing import Optional

VERIFIED = "VERIFIED"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
REJECTED = "REJECTED"
DUPLICATE = "DUPLICATE"
MANUAL_OVERRIDE = "MANUAL_OVERRIDE"

OUTCOMES = (VERIFIED, REVIEW_REQUIRED, REJECTED, DUPLICATE, MANUAL_OVERRIDE)


@dataclass(frozen=True)
class Decision:
    outcome: str
    reason: str
    threshold: Optional[float] = None


def evaluate(
    *,
    session_active: bool,
    duplicate: bool,
    liveness_ok: bool,
    spoof_suspected: bool,
    confidence: float,
    quality_score: float,
    min_confidence: float,
    min_quality: float,
) -> Decision:
    """Return the policy decision for one verification attempt.

    Order matters: hard rejections (no session, spoof, replay) come before
    uncertainty so a spoof attempt is never softened into a review.
    """
    if not session_active:
        return Decision(REJECTED, "No active attendance session.")
    if duplicate:
        return Decision(DUPLICATE, "This student already has a record for this session.")
    if spoof_suspected:
        return Decision(REJECTED, "Suspected presentation attack — manual check required.")
    if not liveness_ok:
        return Decision(REJECTED, "Liveness could not be confirmed.")
    if confidence < min_confidence:
        return Decision(
            REVIEW_REQUIRED,
            f"Match confidence {confidence:.0f} is below the auto-accept threshold {min_confidence:.0f}.",
            min_confidence,
        )
    if quality_score < min_quality:
        return Decision(
            REVIEW_REQUIRED,
            f"Image quality {quality_score:.0f} is below the required minimum {min_quality:.0f}.",
            min_quality,
        )
    return Decision(
        VERIFIED,
        f"Verified with confidence {confidence:.0f} and quality {quality_score:.0f}.",
        min_confidence,
    )
