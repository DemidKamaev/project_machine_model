from abc import ABC, abstractmethod


class AbstractAccount(ABC):
    """
    Account identifier
    Owner details
    Protected balance
    Status balance
    """

    STATUS_ACTIVE = "active"
    STATUS_FROZEN = "frozen"
    STATUS_CLOSED = "closed"

    def __init__(self, account_id: str, owner: str, balance: float = 0.0, status: str = STATUS_ACTIVE):
        self.account_id = account_id
        self.owner = owner
        self._balance = balance
        self.status = status

    @property
    def balance(self):
        return self._balance

    @abstractmethod
    def deposit(self, amount: float) -> None:
        pass

    @abstractmethod
    def withdraw(self, amount: float) -> None:
        pass

    @abstractmethod
    def get_account_info(self) -> dict:
        pass