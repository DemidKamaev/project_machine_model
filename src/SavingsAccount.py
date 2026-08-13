from BankAccount import BankAccount
from exceptions import InvalidOperationError, InsufficientFundsError


class SavingsAccount(BankAccount):
    def __init__(
            self,
            owner: str,
            min_balance: float,
            monthly_rate: float,
            **kwargs,
    ):
        super().__init__(owner=owner, **kwargs)
        if min_balance < 0:
            raise InvalidOperationError("min_balance cannot be negative")
        if monthly_rate < 0:
            raise InvalidOperationError("monhly_rate cannot be negative")
        if self.balance < min_balance:
            raise InvalidOperationError("Initial balance is below minimum balance")
        self.min_balance = min_balance
        self.monthly_rate = monthly_rate

    def apply_monthly_interest(self) -> None:
        self._check_status()
        self._balance += self._balance * self.monthly_rate

    def withdraw(self, amount: float) -> None:
        self._validate_amount(amount)
        self._check_status()

        if amount > self._balance:
            raise InsufficientFundsError("Insufficient funds")

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
