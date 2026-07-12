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
