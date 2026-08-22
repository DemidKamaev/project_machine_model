from datetime import datetime

from Transaction import Transaction


class TransactionQueue:
    def __init__(self):
        self.normal: list[Transaction] = []
        self.priority: list[Transaction] = []
        self.deferred: dict[str, datetime] = {}
        self.cancelled: set[str] = set()

    def add(self, tx: Transaction, priority: bool = False):
        """Добавить перевод в очередь"""
        if priority:
            self.priority.append(tx)
        else:
            self.normal.append(tx)

    def add_deferred(self, tx: Transaction, run_at: datetime):
        """Отложенный перевод"""
        self.normal.append(tx)
        self.deferred[tx.transaction_id] = run_at

    def cancel(self, transaction_id: str):
        """Отменить перевод"""
        self.cancelled.add(transaction_id)
        for tx in self.normal + self.priority:
            if tx.transaction_id == transaction_id:
                tx.mark_cancelled()
                break

    def get_next(self) -> Transaction | None:
        """Взять следующий перевод для обработки"""
        # 1) приоритетные
        while self.priority:
            tx = self.priority.pop(0)
            if tx.transaction_id not in self.cancelled:
                return tx

        # 2) Обычные
        n = len(self.normal)
        checked = 0

        while self.normal and checked < n:
            tx = self.normal.pop(0)
            checked += 1

            if tx.transaction_id in self.cancelled:
                continue

            if tx.transaction_id in self.deferred:
                if datetime.now() < self.deferred[tx.transaction_id]:
                    self.normal.append(tx)
                    continue
                del self.deferred[tx.transaction_id]

            return tx

        return None

    def is_empty(self) -> bool:
        return not self.priority and not self.normal
