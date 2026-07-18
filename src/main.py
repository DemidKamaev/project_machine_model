from src.BankAccount import BankAccount
from src.AbstractAccount import AbstractAccount
from src.exceptions import AccountFrozenError
from src.SavingsAccount import SavingsAccount
from src.PremiumAccount import PremiumAccount
from src.InvestmentAccount import InvestmentAccount

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

"Проверка, что нельзя снять больше лимита 100.000"
acc_2 = PremiumAccount(owner="Test_2", balance=10000)
acc_2.deposit(100000)
acc_2.withdraw(10000)
# acc_2.withdraw(100001)
print(acc_2)

"Проверка, что нельзя снять если заходит за лимит овердрафт"
acc_3 = PremiumAccount(owner="Test_3", balance=15000)
acc_3.deposit(100)
# acc_3.withdraw(25100)
print(acc_3)

acc_4_invest = InvestmentAccount(owner="Test_4")
acc_4_invest.deposit(10000)
acc_4_invest.buy_asset("stocks", 5000)
print(f"Growth: {acc_4_invest.project_yearly_growth()}")
print(acc_4_invest)