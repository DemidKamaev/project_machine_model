import csv
from pathlib import Path
import json
import matplotlib.pyplot as plt

from src.main_analyzer import processor
from PremiumAccount import PremiumAccount


class ReportBuilder:
    def __init__(self, bank, analyzer, audit_log, output_dir: str = "reports"):
        self.bank = bank
        self.analyzer = analyzer
        self.audit_log = audit_log
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)  # create folder if it doesn't exist

    def build_bank_report(self) -> dict:
        return {
            "bank_name": self.bank.name,
            "client_count": len(self.bank.clients),
            "account_count": len(self.bank.accounts),
            "total_balance": self.bank.get_total_balance(),
            "top_clients": self.bank.get_clients_ranking()[:3],
        }

    def build_client_report(self, client_id: str) -> dict:
        client = self.bank.clients[client_id]
        accounts = []
        for acc_id in client.account_ids:
            acc = self.bank.accounts[acc_id]
            accounts.append({
                "account_id": acc.account_id,
                "type": acc.__class__.__name__,
                "balance": acc.balance
            })

        return {
            "client_id": client.client_id,
            "full_name": client.full_name,
            "status": client.status,
            "accounts": accounts,
        }

    def build_risk_report(self) -> dict:
        history = self.analyzer._risk_history
        low = sum(1 for e in history if e["risk"] == "low")
        medium = sum(1 for e in history if e["risk"] == "medium")
        high = sum(1 for e in history if e["risk"] == "high")

        return {
            "total": len(history),
            "low": low,
            "medium": medium,
            "high": high,
            "suspicious": [e for e in history if e["risk"] in ("medium", "high")]
        }

    def export_to_json(self, data: dict, filename: str) -> Path:
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def export_to_csv(self, rows: list[dict], filename: str) -> Path:
        path = self.output_dir / filename
        if not rows:
            return path

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return path

    def export_top_clients_csv(self, filename: str = "top_clients.csv") -> Path:
        ranking = self.bank.get_clients_ranking()[:3]
        rows = [
            {"place": i, "name": name, "balance": total}
            for i, (name, total) in enumerate(ranking, start=1)
        ]
        return self.export_to_csv(rows, filename)

    def chart_risk_pie(self, filename: str = "risk_pie.png") -> Path:
        report = self.build_risk_report()
        labels = ["low", "medium", "high"]
        sizes = [report["low"], report["medium"], report["high"]]

        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, autopct="%1.1f%%")
        ax.set_title("Risk levels")

        path = self.output_dir / filename
        fig.savefig(path)
        plt.close(fig)
        return path

    def chart_top_clients_bar(self, filename: str = "top_clients_bar.png") -> Path:
        ranking = self.bank.get_clients_ranking()[:3]
        names = [name for name, total in ranking]
        totals = [total for name, total in ranking]

        fig, ax = plt.subplots()
        ax.bar(names, totals)
        ax.set_title("Top-3 clients")
        ax.set_ylabel("Balance")
        plt.xticks(rotation=15)

        path = self.output_dir / filename
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    def chart_balance_flow(
            self,
            account_id: str,
            transactions: list,
            filename: str = "balance_flow.png"
    ) -> Path:
        account = self.bank.accounts[account_id]
        processor = self.analyzer.processor

        changes = []
        for tx in transactions:
            if tx.status != "completed":
                continue

            if tx.sender_id == account_id:
                amount_in_acc = processor.convert_currency(
                    tx.amount, tx.currency, account.currency
                )
                commission = processor.calculate_commission(tx)
                commission_in_acc = processor.convert_currency(
                    commission, tx.currency, account.currency
                )
                delta = -(amount_in_acc + commission_in_acc)

                if isinstance(account, PremiumAccount):
                    delta -= account.commission

                changes.append(delta)

            elif tx.recipient_id == account_id:
                amount_in_acc = processor.convert_currency(
                    tx.amount, tx.currency, account.currency
                )
                changes.append(amount_in_acc)

        current = account.balance
        start = current - sum(changes)

        balances = [start]
        for change in changes:
            balances.append(balances[-1] + change)

        fig, ax = plt.subplots()
        ax.plot(range(len(balances)), balances, marker="o")
        ax.set_title(f"Balance flow: {account_id}")
        ax.set_xlabel("Step")
        ax.set_ylabel("Balance")

        path = self.output_dir / filename
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    def save_charts(self, account_id: str, transactions: list) -> list[Path]:
        paths = [
            self.chart_risk_pie(),
            self.chart_top_clients_bar(),
            self.chart_balance_flow(account_id, transactions)
        ]
        return paths

    def export_to_text(self, data: dict, filename: str) -> Path:
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            for key, value in data.items():
                f.write(f"{key}: {value}\n")
        return path