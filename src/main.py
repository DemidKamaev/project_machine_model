from BankAccount import BankAccount
from AbstractAccount import AbstractAccount
from exceptions import AccountFrozenError
from SavingsAccount import SavingsAccount
from PremiumAccount import PremiumAccount
from InvestmentAccount import InvestmentAccount
from Bank import Bank

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

bank = Bank()
client = bank.add_client(
    "Ivanov Ivan",
    1990,
    {"phone": "+7999", "email": "ivan@mail.ru", "pin": "1234"},
)
print(client)

print("\n=== 3. Открытие счетов ===")
acc_savings: SavingsAccount = bank.open_account(
    client.client_id,
    "savings",
    min_balance=500,
    monthly_rate=0.005,
)
acc_premium = bank.open_account(client.client_id, "premium")
acc_investment = bank.open_account(client.client_id, "investment")

acc_savings.deposit(5000)
acc_premium.deposit(3000)
acc_investment.deposit(10000)
acc_investment.buy_asset("stocks", 5000)

print(acc_savings)
print(acc_premium)
print(acc_investment)
print(f"Projected growth: {acc_investment.project_yearly_growth()}")

"""Check negative testcase"""
# BankAccount(owner="")  # error: raise InvalidOperationError("Owner name cannot be empty")
# BankAccount(owner="", balance=-1)  # error: raise InvalidOperationError("Owner name cannot be empty")
# BankAccount(owner="X", status="bad")  # error: raise InvalidOperationError(f"Invalid account status: {status}")
