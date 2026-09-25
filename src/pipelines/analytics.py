"""
src/pipelines/analytics.py
Student Attendance Analysis add-on: recovery calculator, bunk calculator,
semester-end projection, and trend-aware risk tiering.

Operates on the attendance_logs shape already used throughout this app:
a list of dicts each containing at least 'timestamp' and 'is_present'.
This keeps the module decoupled from Supabase - it's pure Python and unit
testable on its own.
"""

import math
from dataclasses import dataclass

THRESHOLD = 0.75  # most Indian colleges require 75% attendance


@dataclass
class RiskTier:
    label: str
    color: str


TIERS = {
    "Safe":     RiskTier("Safe", "#2e7d32"),
    "Watch":    RiskTier("Watch", "#f9a825"),
    "At-Risk":  RiskTier("At-Risk", "#ef6c00"),
    "Critical": RiskTier("Critical", "#c62828"),
}


def summarize_logs(logs: list) -> tuple:
    """
    logs: list of dicts with an 'is_present' key (as returned by
    get_student_attendance / get_attendance_for_teacher).
    Returns (present_count, total_count), sorted chronologically as a
    side effect isn't needed here - see status_timeline() for the ordered version.
    """
    total = len(logs)
    present = sum(1 for l in logs if l.get("is_present"))
    return present, total


def status_timeline(logs: list) -> list:
    """Returns statuses ('present'/'absent') ordered oldest -> newest by timestamp."""
    ordered = sorted(logs, key=lambda l: l.get("timestamp") or "")
    return ["present" if l.get("is_present") else "absent" for l in ordered]


def recovery_calculator(present: int, total: int, threshold: float = THRESHOLD) -> int:
    """Classes needed (consecutively) to bring attendance back to `threshold`."""
    if total == 0:
        return 0
    if present / total >= threshold:
        return 0
    x = (threshold * total - present) / (1 - threshold)
    return max(0, math.ceil(x))


def bunk_calculator(present: int, total: int, threshold: float = THRESHOLD) -> int:
    """Classes that can additionally be missed while staying at/above `threshold`."""
    if total == 0:
        return 0
    if present / total < threshold:
        return 0
    y = (present / threshold) - total
    return max(0, math.floor(y))


def recent_attendance_rate(statuses: list, window: int = 8) -> float:
    if not statuses:
        return 0.0
    recent = statuses[-window:]
    return sum(1 for s in recent if s == "present") / len(recent)


def trend_direction(statuses: list, window: int = 8) -> str:
    recent = statuses[-window:]
    if len(recent) < 4:
        return "stable"
    mid = len(recent) // 2
    first = sum(1 for s in recent[:mid] if s == "present") / mid
    second = sum(1 for s in recent[mid:] if s == "present") / (len(recent) - mid)
    delta = second - first
    if delta <= -0.15:
        return "falling"
    if delta >= 0.15:
        return "rising"
    return "stable"


def semester_end_projection(present: int, total: int, remaining_lectures: int,
                             recent_rate: float = None) -> float:
    """Projects final attendance % using a recent-trend rate rather than the flat average."""
    rate = recent_rate if recent_rate is not None else (present / total if total else 0.0)
    final_present = present + rate * remaining_lectures
    final_total = total + remaining_lectures
    if final_total == 0:
        return 0.0
    return round(100 * final_present / final_total, 1)


def risk_tier(present: int, total: int, statuses: list = None) -> RiskTier:
    """Classifies using BOTH current percentage and trend direction."""
    pct = (present / total * 100) if total else 0.0
    trend = trend_direction(statuses or [])

    if pct < 65:
        return TIERS["Critical"]
    if pct < 75:
        return TIERS["At-Risk"] if trend != "rising" else TIERS["Watch"]
    if pct < 80:
        return TIERS["Watch"]
    return TIERS["Watch"] if trend == "falling" else TIERS["Safe"]


def analyze_student_subject(logs: list, remaining_lectures: int = 20) -> dict:
    """
    Convenience wrapper: give it one student's logs for one subject, get back
    everything the Student Analytics UI needs in one call.
    """
    present, total = summarize_logs(logs)
    statuses = status_timeline(logs)
    recent_rate = recent_attendance_rate(statuses)
    return {
        "present": present,
        "total": total,
        "percentage": round(present / total * 100, 1) if total else 0.0,
        "recovery_needed": recovery_calculator(present, total),
        "can_bunk": bunk_calculator(present, total),
        "projection": semester_end_projection(present, total, remaining_lectures, recent_rate),
        "tier": risk_tier(present, total, statuses),
    }
