import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipelines.analytics import (
    recovery_calculator, bunk_calculator, semester_end_projection,
    recent_attendance_rate, trend_direction, risk_tier, summarize_logs,
    status_timeline, analyze_student_subject
)


def make_logs(pattern):
    """pattern: string like 'PPPAA' -> list of log dicts in that chronological order."""
    logs = []
    for i, ch in enumerate(pattern):
        logs.append({
            "timestamp": f"2026-07-{i+1:02d}T09:00:00",
            "is_present": ch == "P",
        })
    return logs


def test_summarize_logs():
    logs = make_logs("PPPAA")
    assert summarize_logs(logs) == (3, 5)


def test_status_timeline_order_independent_of_input_order():
    logs = make_logs("PAPAP")
    shuffled = [logs[3], logs[0], logs[4], logs[1], logs[2]]
    assert status_timeline(shuffled) == status_timeline(logs)


def test_recovery_calculator_matches_manual_math():
    x = recovery_calculator(present=20, total=40)
    assert x == 40  # 50% -> need 40 more consecutive presents to hit 75%


def test_bunk_calculator_matches_manual_math():
    y = bunk_calculator(present=45, total=50)
    assert y == 10  # 90% -> can miss 10 more and stay at 75%


def test_projection_reflects_recent_trend():
    proj_good_recent = semester_end_projection(20, 40, 20, recent_rate=0.9)
    proj_flat = semester_end_projection(20, 40, 20)
    assert proj_good_recent > proj_flat


def test_risk_tier_critical_below_65():
    assert risk_tier(20, 40).label == "Critical"


def test_risk_tier_trend_sensitive():
    stable = status_timeline(make_logs("PPPPPPPP"))
    falling = status_timeline(make_logs("PPPPAAAA"))
    safe = risk_tier(41, 50, statuses=stable)
    watch = risk_tier(41, 50, statuses=falling)
    assert safe.label == "Safe"
    assert watch.label == "Watch"


def test_analyze_student_subject_end_to_end():
    logs = make_logs("PPPPPPPPPP" + "AAAA")  # 10 present, 4 absent = 71.4%
    result = analyze_student_subject(logs, remaining_lectures=10)
    assert result["present"] == 10
    assert result["total"] == 14
    assert result["percentage"] == 71.4
    assert result["recovery_needed"] > 0
    assert result["can_bunk"] == 0
    assert result["tier"].label in ("At-Risk", "Watch")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
