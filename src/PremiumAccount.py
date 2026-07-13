from BankAccount import BankAccount


class PremiumAccount(BankAccount):
    def __init__(self, raise_limits, overdraft_facility, fix_commission):
        self.raise_limits = raise_limits
        self.overdraft_facility = overdraft_facility
        self.fix_commission = fix_commission
