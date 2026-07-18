from BankAccount import BankAccount
from exceptions import InvalidOperationError, InsufficientFundsError


class InvestmentAccount(BankAccount):

    def __init__(self, owner, **kwargs):
        super().__init__(owner=owner, **kwargs)
        self.portfolio = {
            "stocks": 0.0,
            "bonds": 0.0,
            "etf": 0.0,
        }
        self.expected_growth = {
            "stocks": 0.12,
            "bonds": 0.06,
            "etf": 0.08,
        }

    def buy_asset(self, asset_type: str, amount: float) -> None:
        if asset_type not in self.portfolio:
            raise InvalidOperationError(f"Unknown asset: {asset_type}")
        self._validate_amount(amount)
        self._check_status()
        if amount > self._balance:
            raise InsufficientFundsError(f"Not enough funds")
        self._balance -= amount
        self.portfolio[asset_type] += amount

    def project_yearly_growth(self) -> float:
        total = 0.0
        for asset, value in self.portfolio.items():
            rate = self.expected_growth.get(asset, 0.0)
            total += value * rate
        return total

    def withdraw(self, amount: float) -> None:
        self._validate_amount(amount)
        self._check_status()
        if amount > self._balance:
            raise InsufficientFundsError("Insufficient cash balance")
        self._balance -= amount

    def get_account_info(self) -> dict:
        return {
            "type": "InvestmentAccount",
            "account_id": self.account_id,
            "owner": self.owner,
            "status": self.status,
            "balance": self.balance,
            "currency": self.currency,
            "portfolio": self.portfolio,
            "expected_growth": self.expected_growth
        }

    def __str__(self):
        return (
            f"InvestmentAccount | owner={self.owner} | "
            f"****{self.account_id[-4:]} | "
            f"status={self.status} | "
            f"balance={self.balance} {self.currency} | "
            f"portfolio={self.portfolio} | "
            f"expected_growth={self.expected_growth}"
        )
