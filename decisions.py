""" Writing any decisions about a target to files and read back"""

from datetime import datetime
from pathlib import Path

import pandas as pd

verdicts = ["accept", "reject", "uncertain"]

Flags = {"period_fix":  "period_fix",
    "phase_fix":   "phase_fix",
    "not_eclipse": "not_eclipse",
    "bad_data":    "bad_data"}

columns = ["tic", "sectors", "verdict", "period_factor", "period_label", "phase_offset", "flags", "note", "comments", "timestamp"]

def build_comments(verdict, active, period_label="P", phase_offset=0.0):
    """Detailed summary file produce."""
    parts = []
    if verdict:
        parts.append(verdict)

    for key in Flags:                     
        if key not in active:
            continue
        if key == "period_fix":
            parts.append(period_label)
        elif key == "phase_fix":
            parts.append(f"phase{phase_offset:+.3f}")
        else:
            parts.append(Flags[key])

    return ";".join(parts)

def append_decision(path, *, tic, sectors, verdict, flags,
                    period_factor=1.0, period_label="P",
                    phase_offset=0.0, note=""):
    """Adds the final decision to the end of file and returns written row"""
    path = Path(path)

    row = {
        "tic": str(tic),
        "sectors": str(sectors),
        "verdict": verdict,
        "period_factor": float(period_factor),
        "period_label": period_label,
        "phase_offset": float(phase_offset),
        "flags": " ".join(key for key in flags if key in flags),
        "note": note,
        "comments": build_comments(verdict, flags, period_label, phase_offset),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    frame = pd.DataFrame([row], columns=columns)
    frame.to_csv(path, mode="a", index=False, header=not path.exists())
    return row

def load_decisions(path):
    """returns all decisions back"""
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=columns)
    return pd.read_csv(path, dtype={"tic": str, "sectors": str})

def latest_decisions(path):
    """Latest decision for any TIC."""
    frame = load_decisions(path)
    if frame.empty:
        return frame
    return frame.drop_duplicates(subset="tic", keep="last")


def decided_tics(path):
    """to narrow lists to remaining TICs"""
    frame = latest_decisions(path)
    return set(frame["tic"]) if not frame.empty else set()

def decisions_map(path):
    """TIC -> last decision."""
    frame = latest_decisions(path)
    result = {}

    for _, rec in frame.iterrows():
        raw = rec["flags"]
        result[str(rec["tic"])] = {
            "verdict": rec["verdict"],
            "flags": set(str(raw).split()) if pd.notna(raw) else set(),
            "period_factor": float(rec["period_factor"]),
            "phase_offset": float(rec["phase_offset"]),
            "note": "" if pd.isna(rec["note"]) else str(rec["note"]),
        }

    return result

if __name__ == "__main__":
    test_path = Path("decisions_test.csv")
    test_path.unlink(missing_ok=True)

    append_decision(test_path, tic="4706682", sectors="7",
                    verdict="accept", flags={"period_fix"},
                    period_factor=2.0, period_label="2P")

    append_decision(test_path, tic="4707264", sectors="7",
                    verdict="reject", flags={"not_eclipse", "bad_data"})

    append_decision(test_path, tic="4706682", sectors="7",
                    verdict="accept", flags={"period_fix", "phase_fix"},
                    period_factor=2.0, period_label="2P", phase_offset=0.07,
                    note="secondary is shallow")

    print("--- history ---")
    print(load_decisions(test_path)[["tic", "verdict", "comments", "timestamp"]])

    print("\n--- latest decision for all TICs ---")
    print(latest_decisions(test_path)[["tic", "comments", "note"]])

    print("\ndecided objects:", decided_tics(test_path))