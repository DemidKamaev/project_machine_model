import uuid
from datetime import date

from exceptions import ClientBlockedError, ClientTooYoungError


class Client:
    STATUS_ACTIVE = "active"
    STATUS_BLOCKED = "blocked"

    def __init__(
            self,
            full_name: str,
            birth_year: int,
            contacts: dict,
            client_id: str | None = None,
    ):
        age = date.today().year - birth_year
        if age < 18:
            raise ClientTooYoungError(f"Client must be 18+, age={age}")

        self.client_id = client_id or str(uuid.uuid4())[:8]
        self.full_name = full_name
        self.birth_year = birth_year
        self.status = self.STATUS_ACTIVE
        self.account_ids: list[str] = []
        self.contacts = contacts

    def add_account(self, account_id: str) -> None:
        if account_id not in self.account_ids:
            self.account_ids.append(account_id)

    def block(self) -> None:
        self.status = self.STATUS_BLOCKED

    def is_active(self) -> bool:
        return self.status == self.STATUS_ACTIVE

    def __str__(self) -> str:
        return (
            f"Client | id={self.client_id} | name={self.full_name} | "
            f"status={self.status} | accounts={len(self.account_ids)}"
        )
