"""Shared log helpers — Tee stdout/stderr to a file (append mode).

Used by orchestrators and their sub-tools to consolidate output into one
log file per workflow run. The orchestrator decides the log path
(`.log/<orchestrator>_<timestamp>.log`) and passes it to each sub-tool
via the `--logpath` option; sub-tools open the same file in append mode
so the combined log preserves time order across all steps.

Usage in a tool's main:

    parser.add_argument("--logpath", default=None,
                        help="Append stdout/stderr to this log file "
                             "(used by orchestrator)")
    args = parser.parse_args(...)
    setup_logpath(args.logpath)

If `--logpath` is omitted (single-tool run), stdout/stderr are unchanged.
"""
import sys
from pathlib import Path


class Tee:
    """Forward writes to both an underlying stream and a log file."""

    def __init__(self, stream, log_file):
        self.stream = stream
        self.log_file = log_file

    def write(self, data: str) -> int:
        self.stream.write(data)
        self.log_file.write(data)
        self.log_file.flush()
        return len(data)

    def flush(self) -> None:
        self.stream.flush()
        self.log_file.flush()

    def isatty(self) -> bool:
        return getattr(self.stream, "isatty", lambda: False)()

    def fileno(self) -> int:
        return self.stream.fileno()


def setup_logpath(logpath: str | None) -> None:
    """Wrap sys.stdout / sys.stderr in a Tee writing to logpath.

    Append mode — orchestrator opens the file with a header line, then
    every sub-tool appends as it runs. No-op if logpath is None.
    """
    if not logpath:
        return
    path = Path(logpath)
    path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(path, "a", encoding="utf-8")
    sys.stdout = Tee(sys.stdout, log_file)
    sys.stderr = Tee(sys.stderr, log_file)


def make_log_path(repo_root: Path, label: str) -> Path:
    """Standard log path: <repo>/.log/<label>_<YYYYMMDD_HHMMSS>.log."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return repo_root / ".log" / f"{label}_{timestamp}.log"
