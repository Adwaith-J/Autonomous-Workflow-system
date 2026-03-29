"""logs/trace_logger.py"""

from datetime import datetime

COLORS = {
    "THINK":   "\033[96m", "PLAN":    "\033[94m",
    "EXECUTE": "\033[92m", "REVIEW":  "\033[95m",
    "UPDATE":  "\033[91m", "SYSTEM":  "\033[90m",
}
RESET = "\033[0m"


class TraceLogger:
    def log(self, phase: str, msg: str):
        ts = datetime.utcnow().strftime("%H:%M:%S")
        c = COLORS.get(phase, "")
        print(f"{c}[{phase:7}]{RESET} {ts} | {msg}")
