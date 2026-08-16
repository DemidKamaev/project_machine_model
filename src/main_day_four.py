from Bank import Bank
from Transaction import Transaction
from TransactionQueue import TransactionQueue
from TransactionProcessor import TransactionProcessor
from audit_log import AuditLog
from risk_analyzer import RiskAnalyzer


def main():
    # --- Bank + check ---
    bank = Bank()
    bank.enforce_night_ban = False

    c1 = bank.add_client("Ivanov Ivan", 1990, {"pin": "1234"})
    c2 = bank.add_client("Petrova Anna", 2000, {"pin": "5678"})

    acc1 = bank.open_account(c1.client_id, "bank")
    acc2 = bank.open_account(c2.client_id, "bank")
    acc_premium = bank.open_account(c2.client_id, "premium")

    acc1.deposit(10000)
    acc2.deposit(5000)
    acc_premium.deposit(3000)

    # --- queue + processor ---
    queue = TransactionQueue()
    audit = AuditLog("audit_day3.log")
    processor = TransactionProcessor(bank, queue)
    analyzer = RiskAnalyzer(bank, audit, processor)
    processor.risk_analyzer = analyzer

    transactions = []

    for i in range(8):
        tx = Transaction(
            type="transfer",
            amount=100 * (i + 1),
            currency="RUB",
            commission=0.0,
            sender_id=acc1.account_id,
            recipient_id=acc2.account_id,
        )
        transactions.append(tx)
        queue.add(tx)

        # 1 external - priority
        tx_ext = Transaction(
            type="external",
            amount=500,
            currency="RUB",
            commission=0.0,
            sender_id=acc1.account_id,
            recipient_id=acc2.account_id,
        )
        transactions.append(tx_ext)

        # 1 big - then cancel
        tx_cancel = Transaction(
            type="transfer",
            amount=999999,
            currency="RUB",
            commission=0.0,
            sender_id=acc1.account_id,
            recipient_id=acc2.account_id,
        )
        transactions.append(tx_cancel)
        queue.add(tx_cancel)
        queue.cancel(tx_cancel.transaction_id)

        print(f"Quere size before: {len(queue.normal) + len(queue.priority)}")

        # --- processing ---
        processor.process_all()

        # --- result ---
        print("\n=== Transactions ===")
        for tx in transactions:
            print(tx)
            if tx.failure_reason:
                print(f" reason: {tx.failure_reason}")

        print("\n=== Errors ===")
        for err in processor.errors:
            print(err)

        print(f"\nacc1 balance: {acc1.balance}")
        print(f"acc2 balance: {acc2.balance}")
        print(f"acc_premium balance: {acc_premium.balance}")


if __name__ == "__main__":
    main()
