import uuid
from datetime import datetime


class Transaction:
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    def __init__(
            self,
            type: str,
            amount: float,
            currency: str,
            commission: float,
            sender_id: str,
            recipient_id: str
    ):
        self.transaction_id = str(uuid.uuid4())[:8]
        self.type = type
        self.amount = amount
        self.currency = currency
        self.commission = commission
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.status = self.STATUS_PENDING
        self.failure_reason = None
        self.created_at = datetime.now()
        self.processed_at = None

    def mark_completed(self):
        self.status = self.STATUS_COMPLETED
        self.processed_at = datetime.now()

    def mark_failed(self, reason: str):
        self.status = self.STATUS_FAILED
        self.failure_reason = reason
        self.processed_at = datetime.now()

    def mark_cancelled(self):
        self.status = self.STATUS_CANCELLED
        self.processed_at = datetime.now()

    def __str__(self):
        return (
            f"TX {self.transaction_id} | {self.type} | {self.amount} | {self.currency} | "
            f"{self.sender_id} -> {self.recipient_id} | {self.status}"
        )
