class AccountFrozenError(Exception):
    """The account is frozen - transactions are prohibited"""
    pass


class AccountClosedError(Exception):
    """The account is closed - transactions are prohibited"""
    pass


class InvalidOperationError(Exception):
    """Invalid transaction (amount, currency, etc.)"""
    pass


class InsufficientFundsError(Exception):
    """Insufficient funds in the account"""
    pass


class ClientTooYoungError(Exception):
    """The client's age is less than 18 years old"""
    pass


class ClientBlockedError(Exception):
    """Client is blocked"""
    pass


class OperationNotAllowedError(Exception):
    """Operation is not allowed (night hours, security rules, etc."""
    pass
