from datetime import datetime
from exceptions import OperationNotAllowedError, ClientBlockedError, InvalidOperationError

from Client import Client
from AbstractAccount import AbstractAccount
from BankAccount import BankAccount
from SavingsAccount import SavingsAccount
from PremiumAccount import PremiumAccount
from InvestmentAccount import InvestmentAccount


class Bank:
    ACCOUNT_TYPES = {
        "bank": BankAccount,
        "savings": SavingsAccount,
        "premium": PremiumAccount,
        "investment": InvestmentAccount
    }
    RATES = {"RUB": 1.0, "USD": 90.0, "EUR": 98.0, "KZT": 0.2, "CNY": 12.5}
    BASE_CURRENCY = "RUB"

    def __init__(self, name: str = "Sberbank"):
        self.name = name
        self.clients: dict[str, Client] = {}
        self.accounts: dict[str, AbstractAccount] = {}

        self.failed_logins: dict[str, int] = {}
        self.suspicious_actions: list[str] = []
        self.authenticated_clients: set[str] = set()

        self.enforce_night_ban = True

    # --- internal transfers ----------------------------

    def _check_operating_hours(self) -> None:
        if not self.enforce_night_ban:
            return

        hour = datetime.now().hour
        if 0 <= hour < 5:
            msg = "Operations unavailable from 00:00 to 05:00"
            self._log_suspicious(msg)
            raise OperationNotAllowedError(msg)

    def _log_suspicious(self, message: str) -> None:
        entry = f"{datetime.now().isoformat()} | {message}"
        self.suspicious_actions.append(entry)

    def _convert_currency(self, amount: float, from_cur: str, to_cur: str) -> float:
        if from_cur == to_cur:
            return amount
        in_rub = amount * self.RATES[from_cur]
        return round(in_rub / self.RATES[to_cur], 2)

    # --- clients --------------------------

    def add_client(self, full_name: str, birth_year: int, contract: dict) -> Client:
        client = Client(
            full_name=full_name,
            birth_year=birth_year,
            contacts=contract,
        )
        self.clients[client.client_id] = client
        self.failed_logins[client.client_id] = 0
        return client

    def authenticate_client(self, client_id: str, pin: str) -> bool:
        client = self.clients.get(client_id)

        if client is None:
            self._log_suspicious(f"Unknown client login: {client_id}")
            return False

        if not client.is_active():
            raise ClientBlockedError(f"Client {client_id} is blocked")

        expected_pin = client.contacts.get("pin", "0000")

        if pin != expected_pin:
            self.failed_logins[client_id] += 1

            if self.failed_logins[client_id] >= 3:
                client.block()
                self._log_suspicious(f"Client {client_id} blocked after 3 failed logins")
                raise ClientBlockedError("Blocked after 3 failed login attempts")

            self._log_suspicious(
                f"Failed login {client_id} ({self.failed_logins[client_id]}/3)"
            )
            return False

        self.failed_logins[client_id] = 0
        self.authenticated_clients.add(client_id)
        return True

    # --- accounts ------------------------

    def open_account(self, client_id: str, account_type: str, owner: str | None = None, **kwargs):
        self._check_operating_hours()

        client = self.clients.get(client_id)
        if client is None:
            raise InvalidOperationError("Client not found")
        if not client.is_active():
            raise ClientBlockedError("Client is blocked")

        account_cls = self.ACCOUNT_TYPES.get(account_type)
        if account_cls is None:
            raise InvalidOperationError(f"Unknown account type: {account_type}")

        account = account_cls(owner=owner or client.full_name, **kwargs)
        self.accounts[account.account_id] = account
        client.add_account(account.account_id)
        return account

    def _get_account(self, account_id: str) -> AbstractAccount:
        account = self.accounts.get(account_id)
        if account is None:
            raise InvalidOperationError(f"Account not found: {account_id}")
        return account

    def close_account(self, account_id: str) -> None:
        self._check_operating_hours()

        account = self._get_account(account_id)

        if account.balance != 0:
            self._log_suspicious(
                f"Attempt to close account {account_id} with balance {account.balance}"
            )
            raise InvalidOperationError("Balance must be 0 to close account")

        account.status = AbstractAccount.STATUS_CLOSED

    def freeze_account(self, account_id: str) -> None:
        self._check_operating_hours()

        account = self._get_account(account_id)
        account.status = AbstractAccount.STATUS_FROZEN

    def unfreeze_account(self, account_id: str) -> None:
        self._check_operating_hours()

        account = self._get_account(account_id)
        account.status = AbstractAccount.STATUS_ACTIVE

    def search_accounts(self, query: str):
        query = query.lower()
        result = []

        for account in self.accounts.values():
            if (
                query in account.account_id.lower()
                or query in account.owner.lower()
                or query in account.__class__.__name__.lower()
            ):
                result.append(account)
        return result

    def get_total_balance(self) -> float:
        total = 0.0
        for account in self.accounts.values():
            if account.status != AbstractAccount.STATUS_CLOSED:
                total += self._convert_currency(
                    account.balance,
                    account.currency,
                    self.BASE_CURRENCY,
                )
        return round(total, 2)

    def get_clients_ranking(self) -> list[tuple[str, float]]:
        ranking = []
        for client in self.clients.values():
            total = 0.0
            for acc_id in client.account_ids:
                if acc_id not in self.accounts:
                    continue
                acc = self.accounts[acc_id]
                if acc.status == AbstractAccount.STATUS_CLOSED:
                    continue
                total += self._convert_currency(
                    acc.balance,
                    acc.currency,
                    self.BASE_CURRENCY,
                )
            ranking.append((client.full_name, round(total, 2)))
        ranking.sort(key=lambda item: item[1], reverse=True)
        return ranking
