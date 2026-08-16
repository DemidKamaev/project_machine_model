from datetime import datetime

from Bank import Bank
from Transaction import Transaction
from TransactionProcessor import TransactionProcessor
from audit_log import AuditLog


class RiskAnalyzer:
    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"

    LARGE_AMOUNT = 50_000
    FREQUENT_COUNT = 5
    FREQUENT_WINDOW_SEC = 60

    def __init__(self, bank: Bank, audit_log: AuditLog, processor: TransactionProcessor):
        self.bank = bank
        self.audit_log = audit_log
        self.processor = processor
        self._recent_tx: list[tuple[datetime, str]] = []  # (time, sender_id)
        self._known_recipients_map: dict[str, set[str]] = {}  # sender -> set(recipient_ids)
        self._risk_history: list[dict] = []

    def _is_frequent(self, sender_id: str) -> bool:
        now = datetime.now()
        count = 0
        for tx_time, sid in self._recent_tx:
            if sid == sender_id and (now - tx_time).total_seconds() <= self.FREQUENT_WINDOW_SEC:
                count += 1
        return count >= self.FREQUENT_COUNT

    def _is_new_recipient(self, sender_id: str, recipient_id: str) -> bool:
        known = self._known_recipients_map.get(sender_id, set())
        return recipient_id not in known

    def _is_night(self) -> bool:
        hour = datetime.now().hour
        return 0 <= hour < 5

    def _track(self, tx: Transaction) -> None:
        self._recent_tx.append((datetime.now(), tx.sender_id))

        if tx.sender_id not in self._known_recipients_map:
            self._known_recipients_map[tx.sender_id] = set()
        self._known_recipients_map[tx.sender_id].add(tx.recipient_id)

    def analyze(self, tx: Transaction) -> str:
        score = 0

        if tx.amount >= self.LARGE_AMOUNT:
            score += 2
        if self._is_frequent(tx.sender_id):
            score += 3
        if self._is_new_recipient(tx.sender_id, tx.recipient_id):
            score += 1
        if self._is_night():
            score += 1

        if score >= 4:
            risk = self.RISK_HIGH
        elif score >= 2:
            risk = self.RISK_MEDIUM
        else:
            risk = self.RISK_LOW

        self._risk_history.append({
            "tx_id": tx.transaction_id,
            "sender_id": tx.sender_id,
            "recipient_id": tx.recipient_id,
            "amount": tx.amount,
            "risk": risk,
            "score": score,
            "timestamp": datetime.now().isoformat(),
        })
        self._track(tx)
        return risk

    def should_block(self, risk: str) -> bool:
        return risk == self.RISK_HIGH

    def process_one(self, tx: Transaction) -> bool:
        return self.processor.process_one(tx)