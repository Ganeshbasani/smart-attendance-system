import math


def runway(attended, conducted, remaining, threshold):
    total_planned = conducted + remaining
    pct = (attended / conducted * 100) if conducted else 0.0

    required_future = max(
        0,
        math.ceil((threshold / 100) * total_planned - attended),
    )
    required_future = min(required_future, remaining)
    safe_misses = max(0, remaining - required_future)
    max_possible = ((attended + remaining) / total_planned * 100) if total_planned else 100.0
    recoverable = max_possible >= threshold

    next_window = min(7, remaining)
    needed_next_window = max(
        0,
        math.ceil((threshold / 100) * (conducted + next_window) - attended),
    )
    needed_next_window = min(needed_next_window, next_window)

    return {
        "current_pct": round(pct, 1),
        "required_future": int(required_future),
        "safe_misses": int(safe_misses),
        "recoverable": recoverable,
        "max_possible_pct": round(max_possible, 1),
        "next_window": next_window,
        "needed_next_window": needed_next_window,
        "remaining": remaining,
        "conducted": conducted,
        "attended": attended,
        "threshold": threshold,
    }


def risk_state(current_pct, trend_pp, consecutive_absences, remaining, recoverable, projected_pct, threshold=75.0, weight=1.0):
    signals = []
    if current_pct < threshold:
        signals.append(f"attendance is below the {threshold:.0f}% threshold")
    if trend_pp <= -5:
        signals.append(f"attendance has fallen {abs(trend_pp):.1f} percentage points recently")
    if consecutive_absences >= 3:
        signals.append(f"{consecutive_absences} consecutive absences")
    if remaining <= 5 and current_pct < threshold:
        signals.append(f"only {remaining} planned sessions remain")
    if not recoverable:
        signals.append("mathematical recovery is no longer possible")
    if projected_pct < threshold:
        signals.append(f"the projected end-of-semester attendance is {projected_pct:.1f}%")
    if weight >= 1.2:
        signals.append("this is a high-weight subject")

    critical = (
        (not recoverable and current_pct < threshold)
        or projected_pct < max(60.0, threshold - 15)
        or (current_pct < 60 and consecutive_absences >= 2)
    )
    at_risk = (
        current_pct < threshold
        or projected_pct < threshold
        or trend_pp <= -8
        or consecutive_absences >= 4
    )
    watch = (
        current_pct < threshold + 5
        or projected_pct < threshold + 3
        or trend_pp <= -5
        or consecutive_absences >= 2
    )

    if critical:
        state = "Critical"
    elif at_risk:
        state = "At Risk"
    elif watch:
        state = "Watch"
    else:
        state = "Safe"

    return {"state": state, "signals": signals[:3]}


def explain_risk(risk, runway_info):
    state = risk["state"]
    if state == "Safe":
        return "Attendance is currently above the policy threshold with enough runway for normal variation."
    if state == "Watch":
        return "Attendance is close to the policy boundary or the recent pattern is weakening. A small change could create a shortage."
    if state == "At Risk":
        signals = "; ".join(risk["signals"]) or "multiple attendance indicators have weakened"
        action = (
            f"Attend the next {runway_info['needed_next_window']} of the next "
            f"{runway_info['next_window']} planned sessions."
            if runway_info["next_window"] else
            "Review your attendance history with faculty."
        )
        return f"Risk increased because {signals}. Recommended action: {action}"
    return "This subject is in a critical state; the runway is too short or recovery is no longer mathematically available. Escalate for human review."
