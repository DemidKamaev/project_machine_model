from src.BankAccount import BankAccount
from src.AbstractAccount import AbstractAccount
from src.exceptions import AccountFrozenError

acc = BankAccount(owner="Demid")
acc.deposit(10000)
acc.withdraw(350)
print(acc)


acc_frozen = BankAccount(owner="Test", status=AbstractAccount.STATUS_FROZEN)
try:
    acc_frozen.deposit(1000)
except AccountFrozenError as e:
    print(e)

