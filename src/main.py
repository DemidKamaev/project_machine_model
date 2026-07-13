from src.BankAccount import BankAccount
from src.AbstractAccount import AbstractAccount
from src.exceptions import AccountFrozenError
from src.SavingsAccount import SavingsAccount

acc = BankAccount(owner="Demid")
acc.deposit(10000)
acc.withdraw(350)
print(acc)


# acc_frozen = BankAccount(owner="Test", status=AbstractAccount.STATUS_FROZEN)
# try:
#     acc_frozen.deposit(1000)
# except AccountFrozenError as e:
#     print(e)

acc_1 = SavingsAccount(owner="Test_1", min_balance=500, monthly_rate=0.06)
acc_1.deposit(1000)
acc_1.apply_monthly_interest()
print(acc_1)
