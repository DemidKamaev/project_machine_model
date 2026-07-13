from BankAccount import BankAccount
from AbstractAccount import AbstractAccount
from exceptions import InvalidOperationError


class SavingsAccount(BankAccount):
    def __init__(
            self,
            owner: str,
            min_balance: float,
            monthly_rate: float,
            account_id: str | None = None,
            balance: float = 0.0,
            status: str = AbstractAccount.STATUS_ACTIVE,
            currency: str = "RUB",
    ):
        super().__init__(
            account_id=account_id,
            owner=owner,
            balance=balance,
            status=status,
            currency=currency,
        )
        self.min_balance = min_balance
        self.monthly_rate = monthly_rate

    def apply_monthly_interest(self) -> None:
        self._check_status()
        self._balance += self._balance * self.monthly_rate

    def withdraw(self, amount: float) -> None:
        self._validate_amount(amount)
        self._check_status()

        if self._balance - amount < self.min_balance:
            raise InvalidOperationError("Cannot go below minimum balance")

        self._balance -= amount

    def get_account_info(self) -> dict:
        return {
            "type": "SavingsAccount",
            "account_id": self.account_id,
            "owner": self.owner,
            "status": self.status,
            "balance": self.balance,
            "currency": self.currency,
            "min_balance": self.min_balance,
            "monthly_rate": self.monthly_rate
        }

    def __str__(self):
        return (
            f"SavingsAccount | owner={self.owner} | "
            f"****{self.account_id[-4:]} | "
            f"status={self.status} | "
            f"balance={self.balance} {self.currency} | "
            f"min_balance={self.min_balance} | "
            f"monthly_rate={self.monthly_rate}"
        )
