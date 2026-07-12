from AbstractAccount import AbstractAccount
import uuid
from exceptions import (
    AccountFrozenError,
    AccountClosedError,
    InvalidOperationError,
    InsufficientFundsError
)


class BankAccount(AbstractAccount):
    """
    Validation of incoming data,
    Logical statuses and operation prohibition for invalid statuses,
    Automatic generation of a short UUID when the account number is missing
    """
    ALLOWED_CURRENCIES = {"RUB", "USD", "EUR", "KZT", "CNY"}

    def __init__(
            self,
            owner: str,
            account_id: str | None = None,
            balance: float = 0.0,
            status: str = AbstractAccount.STATUS_ACTIVE,
            currency: str = "RUB",
    ):
        if account_id is None:
            account_id = str(uuid.uuid4())[:8]

        if currency not in self.ALLOWED_CURRENCIES:
            raise InvalidOperationError(f"Unsupported currency: {currency}")

        super().__init__(
            account_id=account_id,
            owner=owner,
            balance=balance,
            status=status,
        )

        self.currency = currency

    def _validate_amount(self, amount: float) -> None:
        if not isinstance(amount, (int, float)):
            raise InvalidOperationError("The sum must be a number.")
        if amount <= 0:
            raise InvalidOperationError("The amount must be greater than zero.")

    def _check_status(self) -> None:
        if self.status == self.STATUS_FROZEN:
            raise AccountFrozenError("The balance is frozen")
        if self.status == self.STATUS_CLOSED:
            raise AccountClosedError("The balance is closed")

    def deposit(self, amount: float) -> None:
        self._validate_amount(amount)
        self._check_status()
        self._balance += amount

    def withdraw(self, amount: float) -> None:
        self._validate_amount(amount)
        self._check_status()
        if amount > self._balance:
            raise InsufficientFundsError("Insufficient funds")
        self._balance -= amount

    def get_account_info(self) -> dict:
        return {
            "type": "BankAccount",
            "account_id": self.account_id,
            "owner": self.owner,
            "status": self.status,
            "balance": self.balance,
            "currency": self.currency
        }

    def __str__(self) -> str:
        return (
            f"BankAccount | owner={self.owner} | "
            f"****{self.account_id[-4:]} | "
            f"status={self.status} | "
            f"balance={self.balance} {self.currency}"
        )