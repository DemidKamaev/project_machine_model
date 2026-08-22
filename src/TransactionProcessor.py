from datetime import datetime
from typing import Optional

from Bank import Bank
from TransactionQueue import TransactionQueue
from AbstractAccount import AbstractAccount
from PremiumAccount import PremiumAccount
from Transaction import Transaction
from exceptions import InvalidOperationError


class TransactionProcessor:
    EXTERNAL_RATE = 0.02  # 2% commission in external
    RATES = {"RUB": 1.0, "USD": 90.0, "EUR": 98.0, "KZT": 0.2, "CNY": 12.5}
    NON_RETRYABLE = (
        "Blocked: high risk",
        "Sender account frozen",
        "Insufficient funds",
    )

    def __init__(self, bank: Bank, queue: TransactionQueue, risk_analyzer=None):
        self.bank = bank
        self.queue = queue
        self.risk_analyzer = risk_analyzer
        self.errors: list[str] = []
        self.max_retries = 3

    # --- commission (n. TransactionProcessor) ---
    def calculate_commission(self, tx: Transaction) -> float:
        if tx.type == "external":
            return round(tx.amount * self.EXTERNAL_RATE, 2)
        return tx.commission

    # --- conversion ---
    def convert_currency(self, amount: float, from_cur: str, to_cur: str) -> float:
        if from_cur not in self.RATES or to_cur not in self.RATES:
            raise InvalidOperationError(f"Unsupperted currency: {from_cur} or {to_cur}")

        if from_cur == to_cur:
            return amount
        in_rub = amount * self.RATES[from_cur]
        return round(in_rub / self.RATES[to_cur], 2)

    # --- rules ---
    def validate(self, tx: Transaction) -> Optional[str]:
        """None = ok, or text error"""
        sender = self.bank.accounts.get(tx.sender_id)
        recipient = self.bank.accounts.get(tx.recipient_id)

        if sender is None:
            return "Sender not found"
        if recipient is None:
            return "Recipient not found"
        if sender.status == AbstractAccount.STATUS_FROZEN:
            return "Sender account frozen"
        if sender.status == AbstractAccount.STATUS_CLOSED:
            return "Sender account closed"
        if recipient.status == AbstractAccount.STATUS_FROZEN:
            return "Recipient account frozen"
        if recipient.status == AbstractAccount.STATUS_CLOSED:
            return "Recipient account closed"
        if tx.currency not in self.RATES:
            return "Unsupported transaction currency"

        commission = self.calculate_commission(tx)
        amount_in_sender = self.convert_currency(tx.amount, tx.currency, sender.currency)
        commission_in_sender = self.convert_currency(commission, tx.currency, sender.currency)
        total = amount_in_sender + commission_in_sender

        if not isinstance(sender, PremiumAccount):
            if sender.balance < total:
                return "Insufficient funds"

        return None

    def process_one(self, tx: Transaction) -> bool:

        if self.bank.enforce_night_ban:
            hour = datetime.now().hour
            if 0 <= hour < 5:
                msg = "Operations unavailable from 00:00 to 05:00"
                tx.mark_failed(msg)
                self.errors.append(f"{tx.transaction_id}: {msg}")
                return False

        if self.risk_analyzer is not None:
            risk = self.risk_analyzer.analyze(tx)

            self.risk_analyzer.audit_log.record(
                self.risk_analyzer.audit_log.LEVEL_INFO,
                f"Risk check: {risk}",
                tx_id=tx.transaction_id,
                sender_id=tx.sender_id,
                amount=tx.amount,
                risk=risk,
            )

            if self.risk_analyzer.should_block(risk):
                tx.mark_failed("Blocked: high risk")
                self.risk_analyzer.audit_log.record(
                    self.risk_analyzer.audit_log.LEVEL_CRITICAL,
                    "Transaction blocked (high risk)",
                    tx_id=tx.transaction_id,
                    risk=risk,
                )
                self.errors.append(f"{tx.transaction_id}: Blocked: high risk")
                return False

        error = self.validate(tx)

        if error:
            tx.mark_failed(error)
            self.errors.append(f"{tx.transaction_id}: {error}")
            if self.risk_analyzer is not None:
                self.risk_analyzer.audit_log.record(
                    self.risk_analyzer.audit_log.LEVEL_ERROR,
                    f"Transaction failed: {error}",
                    tx_id=tx.transaction_id,
                )
            return False

        sender = self.bank.accounts[tx.sender_id]
        recipient = self.bank.accounts[tx.recipient_id]

        tx.commission = self.calculate_commission(tx)
        amount_in_sender = self.convert_currency(tx.amount, tx.currency, sender.currency)
        commission_in_sender = self.convert_currency(tx.commission, tx.currency, sender.currency)
        amount_to_receive = self.convert_currency(tx.amount, tx.currency, recipient.currency)

        try:
            sender.withdraw(amount_in_sender + commission_in_sender)
            recipient.deposit(amount_to_receive)
            tx.mark_completed()
            return True
        except Exception as e:
            tx.mark_failed(str(e))
            self.errors.append(f"{tx.transaction_id}: {e}")
            if self.risk_analyzer is not None:
                self.risk_analyzer.audit_log.record(
                    self.risk_analyzer.audit_log.LEVEL_ERROR,
                    f"Transaction failed: {e}",
                    tx_id=tx.transaction_id,
                )
            return False

    # ── retry ──
    def process_with_retry(self, tx: Transaction) -> bool:
        for attempt in range(1, self.max_retries + 1):
            if self.process_one(tx):
                return True
            reason = tx.failure_reason or ""
            if any(r in reason for r in self.NON_RETRYABLE):
                return False
            if tx.status != Transaction.STATUS_FAILED:
                break
            tx.status = Transaction.STATUS_PENDING
        if tx.status == Transaction.STATUS_FAILED and tx.failure_reason:
            return False
        tx.mark_failed("Max retries exceeded")
        return False

    # ── all queue ──
    def process_all(self):
        while not self.queue.is_empty():
            tx = self.queue.get_next()
            if tx is None:
                break
            self.process_with_retry(tx)
