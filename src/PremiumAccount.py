from BankAccount import BankAccount
from exceptions import InvalidOperationError, InsufficientFundsError


class PremiumAccount(BankAccount):
    def __init__(
            self,
            owner: str,
            withdraw_limit: float = 100_000.0,
            overdraft_limit: float = 10_000.0,
            commission: float = 50.0,
            **kwargs,
    ):
        super().__init__(owner=owner, **kwargs)
        self.withdraw_limit = withdraw_limit
        self.overdraft_limit = overdraft_limit
        self.commission = commission

    def withdraw(self, amount: float) -> None:
        self._validate_amount(amount)
        self._check_status()

        if amount > self.withdraw_limit:
            raise InvalidOperationError("Withdrawal limit exceeded")

        total = amount + self.commission

        """
        The balance can be negative, but it cannot be lower than -overdraft_limit
        """
        if self._balance - total < -self.overdraft_limit:
            raise InsufficientFundsError("Overdraft limit exceeded")

        self._balance -= total

    def get_account_info(self) -> dict:
        return {
            "type": "PremiumAccount",
            "account_id": self.account_id,
            "owner": self.owner,
            "status": self.status,
            "balance": self.balance,
            "currency": self.currency,
            "withdraw_limit": self.withdraw_limit,
            "overdraft_limit": self.overdraft_limit,
            "commission": self.commission
        }

    def __str__(self):
        return (
            f"PremiumAccount | owner={self.owner} | "
            f"****{self.account_id[-4:]} | "
            f"status={self.status} | "
            f"balance={self.balance} {self.currency} | "
            f"withdraw_limit={self.withdraw_limit} | "
            f"overdraft_limit={self.overdraft_limit} |"
            f"commission={self.commission}"
        )
