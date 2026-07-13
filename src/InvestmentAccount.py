from BankAccount import BankAccount


class InvestmentAccount(BankAccount):
    VIRTUAL_ACTIVE = {"stocks", "bonds", "etf"}

    def __init__(self, invest_bags):
        self.invest_bags = invest_bags

        def project_yearly_growth():
            pass
