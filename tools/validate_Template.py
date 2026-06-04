"""Phase 0 orchestrator — run every Template-side validation check in order.

Each step under tools/validation/ or tools/build/ is invoked with
`Template` as its only positional argument; their stdout is forwarded
verbatim so individual findings stay visible. A summary block at the end
reports pass/fail per check and an overall severity.

Workflow severity per check (overrides each tool's internal severity —
this orchestrator is the single source of truth for whether Template
validation should block the rest of the workflow):

  check_required_cols          Critical
  check_duplicates             Critical
  check_whitespace_text        Critical
  check_deprecated             Warn
  check_missing                Info
  check_flag                   Critical
  check_method                 Critical
  build_runtime_tsv            Critical    (--ignore: skip legacy validate_xlsx,
                                            relies on the earlier check_* steps)
  check_runtime_tsv_conflict   Critical    (runs against the dry-run output of
                                            the build step above)

Template auto-routing:
  Both build_runtime_tsv.py and check_runtime_tsv_conflict.py recognise
  `Template` and automatically write/read .tmp/temp_build/Trans To Vostok/Template/
  (a Warn is printed by each tool). No --dry-run flag needs to be passed
  here.

Exit code:
  0  no triggered severity OR only Info-level findings
  2  Warn-level findings, no Critical
  1  one or more Critical-level findings

Usage:
  python tools/validate_Template.py
"""
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATION_DIR = SCRIPT_DIR / "validation"
BUILD_DIR = SCRIPT_DIR / "build"
TARGET = "Template"

# (label, script_path, extra_args, workflow_severity)
CHECKS: list[tuple[str, Path, list[str], str]] = [
    ("check_required_cols",        VALIDATION_DIR / "check_required_cols.py",        [],          "Critical"),
    ("check_duplicates",           VALIDATION_DIR / "check_duplicates.py",           [],          "Critical"),
    ("check_whitespace_text",      VALIDATION_DIR / "check_whitespace_text.py",      [],          "Critical"),
    ("check_deprecated",           VALIDATION_DIR / "check_deprecated.py",           [],          "Warn"),
    ("check_missing",              VALIDATION_DIR / "check_missing.py",              [],          "Info"),
    ("check_flag",                 VALIDATION_DIR / "check_flag.py",                 [],          "Critical"),
    ("check_method",               VALIDATION_DIR / "check_method.py",               [],          "Critical"),
    ("build_runtime_tsv",          BUILD_DIR / "build_runtime_tsv.py",               ["--ignore"], "Critical"),
    ("check_runtime_tsv_conflict", BUILD_DIR / "check_runtime_tsv_conflict.py",      [],          "Critical"),
]

SEVERITY_RANK = {"OK": 0, "Info": 1, "Warn": 2, "Critical": 3}
EXIT_FOR_SEVERITY = {"OK": 0, "Info": 0, "Warn": 2, "Critical": 1}


def _say(msg: str = "") -> None:
    """print + flush so child-process output stays in order with parent's."""
    print(msg, flush=True)


def main() -> int:
    _say(f"=== Phase 0: {TARGET} Validation ({len(CHECKS)} steps) ===")
    _say()

    results: list[tuple[str, str, int]] = []  # (label, severity, exit_code)
    for idx, (label, script, extra_args, severity) in enumerate(CHECKS, start=1):
        if not script.exists():
            _say(f"[ERROR] step script missing: {script.relative_to(SCRIPT_DIR.parent)}")
            return 1

        _say(f"--- [{idx}/{len(CHECKS)}] {label} ({severity}) ---")
        cmd = [sys.executable, str(script), TARGET] + extra_args
        completed = subprocess.run(cmd)
        _say()
        results.append((label, severity, completed.returncode))

    _say("=== Summary ===")
    triggered = "OK"
    for label, severity, rc in results:
        status = "OK" if rc == 0 else severity
        _say(f"  {label:28s}  [{severity:8s}]  {status:8s}  (exit={rc})")
        if rc != 0 and SEVERITY_RANK[severity] > SEVERITY_RANK[triggered]:
            triggered = severity

    _say()
    _say(f"Overall: {triggered}")
    return EXIT_FOR_SEVERITY[triggered]


if __name__ == "__main__":
    sys.exit(main())
