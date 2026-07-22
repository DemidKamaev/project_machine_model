from typing import Optional

from Bank import Bank
from TransactionQueue import TransactionQueue
from AbstractAccount import AbstractAccount
from PremiumAccount import PremiumAccount
from Transaction import Transaction


class TransactionProcessor:
    EXTERNAL_RATE = 0.02  # 2% commission in external
    RATES = {"RUB": 1.0, "USD": 90.0, "EUR": 98.0, "KZT": 0.2, "CNY": 12.5}

    def __init__(self, bank: Bank, queue: TransactionQueue):
        self.bank = bank
        self.queue = queue
        self.errors: list[str] = []
        self.max_retries = 3

    # --- commission (n. TransactionProcessor) ---
    def calculate_commission(self, tx: Transaction) -> float:
        if tx.type == "external":
            return round(tx.amount * self.EXTERNAL_RATE, 2)
        return tx.commission

    # --- conversion ---
    def convert_currency(self, amount: float, from_cur: str, to_cur: str) -> float:
        if from_cur == to_cur:
            return amount
        in_rub = amount * self.RATES[from_cur]
        return round(in_rub / self.RATES[to_cur], 2)

    # --- rules ---
    def validate(self, tx: Transaction) -> Optional[str]:
        """None = ok, иначе текст ошибки"""
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

        commission = self.calculate_commission(tx)
        total = tx.amount + commission

        if not isinstance(sender, PremiumAccount):
            if sender.balance < total:
                return "Insufficient funds"
            
        return None

    def process_one(self, tx: Transaction) -> bool:
        error = self.validate(tx)
        if error:
            tx.mark_failed(error)
            self.errors.append(f"{tx.transaction_id}: {error}")
            return False

        sender = self.bank.accounts[tx.sender_id]
        recipient = self.bank.accounts[tx.recipient_id]

        tx.commission = self.calculate_commission(tx)
        amount_to_receive = self.convert_currency(
            tx.amount, tx.currency, recipient.currency
        )

        try:
            sender.withdraw(tx.amount + tx.commission)
            recipient.deposit(amount_to_receive)
            tx.mark_completed()
            return True
        except Exception as e:
            tx.mark_failed(str(e))
            self.errors.append(f"{tx.transaction_id}: {e}")
            return False

    # ── retry ──
    def process_with_retry(self, tx: Transaction) -> bool:
        for attempt in range(1, self.max_retries + 1):
            if self.process_one(tx):
                return True
            if tx.status != Transaction.STATUS_FAILED:
                break
            tx.status = Transaction.STATUS_PENDING  # сброс для повтора
        tx.mark_failed("Max retries exceeded")
        return False

    # ── all queue ──
    def process_all(self):
        while not self.queue.is_empty():
            tx = self.queue.get_next()
            if tx is None:
                break
            self.process_with_retry(tx)
