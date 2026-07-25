from datetime import datetime
from typing import Optional


class AuditLog:
    LEVEL_INFO = "info"
    LEVEL_WARNING = "warning"
    LEVEL_ERROR = "error"
    LEVEL_CRITICAL = "critical"

    def __init__(self, file_path: str = "audit.log"):
        self._entries: list[dict] = []  # memory
        self.file_path = file_path

    def _append_to_file(self, entry: dict) -> None:
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(
                f"{entry['timestamp']} | {entry['level']} | {entry['message']}\n"
            )
        pass

    def record(self, level: str, message: str, **extra):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            **extra,  # tx_id, client_id, amount...
        }
        self._entries.append(entry)
        self._append_to_file(entry)

    def filter(self, level: Optional[str] = None, keyword: Optional[str] = None) -> list[dict]:
        result = self._entries
        if level:
            result = [e for e in result if e["level"] == level]
        if keyword:
            result = [e for e in result if keyword.lower() in e["message"].lower()]
        return result
