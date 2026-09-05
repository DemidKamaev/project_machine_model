import random
from Bank import Bank
from Transaction import Transaction
from TransactionQueue import TransactionQueue
from TransactionProcessor import TransactionProcessor
from audit_log import AuditLog
from risk_analyzer import RiskAnalyzer
from audit_report import AuditReport
from report_builder import ReportBuilder


def main():
    bank = Bank()
    bank.enforce_night_ban = False

    # --- clients (5-10) ---
    clients = []
    names = [
        ("Ivanov Ivan", 1990),
        ("Petrova Anna", 1995),
        ("Sidorov Petr", 1988),
        ("Kozlova Maria", 2000),
        ("Smirnov Oleg", 1992),
        ("Volkova Lena", 1998),
        ("Morozov Igor", 1985),
    ]
    for i, (name, year) in enumerate(names):
        client = bank.add_client(name, year, {"pin": f"100{i}"})
        clients.append(client)

    # --- account (10-15) ---
    accounts = []
    types = ["bank", "savings", "premium", "investment"]

    for i, client in enumerate(clients):
        # каждому 1-2 счёта
        account_type = types[i % len(types)]

        if account_type == "savings":
            acc = bank.open_account(
                client.client_id,
                "savings",
                balance=1000.0,
                min_balance=1000.0,
                monthly_rate=0.01,
            )
        else:
            acc = bank.open_account(client.client_id, account_type)

        acc.deposit(20_000 + i * 5_000)
        accounts.append(acc)

        if i % 2 == 0:
            acc2 = bank.open_account(client.client_id, "bank")
            acc2.deposit(10_000)
            accounts.append(acc2)

    print(f"Clients: {len(clients)}, Account: {len(accounts)}")

    queue = TransactionQueue()
    audit = AuditLog("audit_module6.log")
    processor = TransactionProcessor(bank, queue)
    analyzer = RiskAnalyzer(bank, audit, processor)
    processor.risk_analyzer = analyzer
    transactions = []

    for i in range(40):
        sender = random.choice(accounts)
        recipient = random.choice(accounts)

        if sender.account_id == recipient.account_id:
            continue

        if i % 5 == 0:
            amount = 1000
            to_id = "invalid-acc"
        elif i % 7 == 0:
            amount = 60_000
            to_id = recipient.account_id
        else:
            amount = 100 + i * 10
            to_id = recipient.account_id

        tx = Transaction(
            type="transfer",
            amount=amount,
            currency="RUB",
            commission=0.0,
            sender_id=sender.account_id,
            recipient_id=to_id,
        )
        transactions.append(tx)
        queue.add(tx)
        print(f"Queued: {tx.transaction_id} amount={tx.amount}")

    print(f"Queued transactions: {len(transactions)}")
    print(f"Queued size: {len(queue.normal) + len(queue.priority)}")

    print("\n=== Processing ===")

    while not queue.is_empty():
        tx = queue.get_next()
        if tx is None:
            break

        ok = analyzer.process_one(tx)

        if ok:
            print(f"OK {tx.transaction_id} | {tx.amount} | completed")
        elif tx.failure_reason and "Blocked" in tx.failure_reason:
            print(f"Block {tx.transaction_id} | {tx.amount} | {tx.failure_reason}")
        else:
            print(f"FAIL {tx.transaction_id} | {tx.amount} | {tx.failure_reason}")

    completed = 0
    failed = 0
    blocked = 0

    for tx in transactions:
        if tx.status == "completed":
            completed += 1
        elif tx.failure_reason and "Blocked" in tx.failure_reason:
            blocked += 1
        else:
            failed += 1

    print("\n=== Summary ===")
    print(f"Completed: {completed}")
    print(f"Failed: {failed}")
    print(f"Blocked: {blocked}")

    print("\n=== Client accounts ===")
    client = clients[0]
    print(client)

    for acc_id in client.account_ids:
        acc = bank.accounts[acc_id]
        print(f" {acc.account_id} | {acc.__class__.__name__} | balance={acc.balance}")

    print("\n=== Client history ===")
    client_acc_id = set(client.account_ids)

    for tx in transactions:
        if tx.sender_id in client_acc_id:
            print(f"{tx.transaction_id} | {tx.amount} | {tx.status} | {tx.failure_reason}")

    print("\n=== Suspicious operations ===")
    report = AuditReport(analyzer, audit)

    for item in report.suspicious_operations():
        print(
            f"{item['tx_id']} | amount={item['amount']} | "
            f"risk={item['risk']} | score={item['score']}"
        )

    print("\n=== Top-3 clients ===")
    ranking = bank.get_clients_ranking()
    for i, (name, total) in enumerate(ranking[:3], start=1):
        print(f"{i}. {name} - {total}")

    print("\n=== Transaction stats ===")
    print(f"Total: {len(transactions)}")
    print(f"Completed: {sum(1 for tx in transactions if tx.status == 'completed')}")
    print(f"Failed: {sum(1 for tx in transactions if tx.status == 'failed')}")

    print("\n=== Total balance ===")
    print(bank.get_total_balance())

    builder = ReportBuilder(bank, analyzer, audit)
    print(builder.build_bank_report())

    path = builder.export_to_json(builder.build_bank_report(), "bank_report.json")
    print("Saved:", path)

    print("Saved", builder.export_top_clients_csv())

    acc_id = accounts[0].account_id

    for path in builder.save_charts(
        accounts[0].account_id, transactions
    ):
        print("Saved", path)

    print("Saved:", builder.export_to_text(builder.build_bank_report(), "bank_report.txt"))


if __name__ == "__main__":
    main()