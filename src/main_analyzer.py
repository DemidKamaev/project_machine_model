from audit_log import AuditLog
from TransactionProcessor import TransactionProcessor
from risk_analyzer import RiskAnalyzer
from Bank import Bank
from TransactionQueue import TransactionQueue
from Transaction import Transaction
from audit_report import AuditReport


bank = Bank()
bank.enforce_night_ban = False

c1 = bank.add_client("Ivanov Ivan", 1990, {"pin": "1234"})
c2 = bank.add_client("Petrova Anna", 2000, {"pin": "5678"})

acc1 = bank.open_account(c1.client_id, "bank")
acc2 = bank.open_account(c2.client_id, "bank")
acc1.deposit(190_000)

queue = TransactionQueue()
audit = AuditLog("audit.log")
processor = TransactionProcessor(bank, queue)
analyzer = RiskAnalyzer(bank, audit, processor)

report = AuditReport(analyzer, audit)

print("=== Sispicious ===")
for item in report.suspicious_operations():
    print(item)

print("=== Profile acc 1 ===")
print(report.client_risk_profile(acc1.account_id))

print("=== Errors ===")
print(report.error_status())


# ... create bank, accounts, analyzer ...
def run(label, tx):
    ok = analyzer.process_one(tx)
    print(f"\n[{label}] ok={ok} status={tx.status} reason={tx.failure_reason}")
    return ok

run(
    "normal",
    Transaction(
            type="transfer",
            amount=500,
            currency="RUB",
            commission=0.0,
            sender_id=acc1.account_id,
            recipient_id=acc2.account_id,
    )
)

report = AuditReport(analyzer, audit)

run(
    "large amount",
    Transaction(
        type="transfer",
        amount=60_000,
        currency="RUB",
        commission=0.0,
        sender_id=acc1.account_id,
        recipient_id=acc2.account_id,
    )
)

acc3 = bank.open_account(c2.client_id, "bank")

run(
    "new recipient + large",
    Transaction(
        type="transfer",
        amount=55_000,
        currency="RUB",
        commission=0.0,
        sender_id=acc1.account_id,
        recipient_id=acc3.account_id,
    )
)

print("balances", acc1.balance, acc2.balance)

###
for i in range(5):
    run(f"burst {i+1}",
        Transaction(
            type="transfer",
            amount=100,
            currency="RUB",
            commission=0.0,
            sender_id=acc1.account_id,
            recipient_id=acc2.account_id,
        )
    )

run("frequent + large -> BLOCK",
    Transaction(
        type="transfer",
        amount=60_000,
        currency="RUB",
        commission=0.0,
        sender_id=acc1.account_id,
        recipient_id=acc3.account_id,
    )
)


# tx = Transaction(
#     type="transfer",
#     amount=500,
#     currency="RUB",
#     commission=0.0,
#     sender_id=acc1.account_id,
#     recipient_id=acc2.account_id,
# )
#
# tx1 = Transaction(
#     type="transfer",
#     amount=500,
#     currency="RUB",
#     commission=0.0,
#     sender_id=acc1.account_id,
#     recipient_id=acc2.account_id,
# )

# ok = analyzer.process_one(tx)
# ok1 = analyzer.process_one(tx1)
# print(ok, tx.status, tx.failure_reason)
# print(ok, tx1.status, tx1.failure_reason)
# print("balances", acc1.balance, acc2.balance)