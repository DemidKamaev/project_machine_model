from src.BankAccount import BankAccount
from src.AbstractAccount import AbstractAccount
from src.exceptions import AccountFrozenError
from src.SavingsAccount import SavingsAccount
from src.PremiumAccount import PremiumAccount
from src.InvestmentAccount import InvestmentAccount
from src.Client import Client
from src.Bank import Bank
from exceptions import ClientBlockedError

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

client = Client(
    full_name="Ivanov Ivan",
    birth_year=1990,
    contacts={"phone": "+7999", "email": "ivan@mail.ru", "pin": "1234"},
)

print(client)

bank = Bank()
# acc_5 = bank.open_account(
#     client.client_id,
#     "savings",
#     min_balance=500,
#     monthly_rate=0.005
# )
# acc_5.deposit(5000)
#
# # freeze
# bank.freeze_account(acc_5.account_id)
# print(acc_5.status)
#
# # unfreeze
# bank.unfreeze_account(acc_5.account_id)
#
# # search
# for a in bank.search_accounts("Ivanov"):
#     print(a)
#
# # close
# while acc_5.balance > acc_5.min_balance:
#     acc_5.withdraw(min(500, acc_5.balance - acc_5.min_balance))
# bank.close_account(acc_5.account_id)
# print(acc_5.status)


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