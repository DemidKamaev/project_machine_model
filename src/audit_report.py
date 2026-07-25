from audit_log import AuditLog
from risk_analyzer import RiskAnalyzer


class AuditReport:
    def __init__(self, analyzer: RiskAnalyzer, audit_log: AuditLog):
        self.analyzer = analyzer
        self.audit_log = audit_log

    # 1) suspicious transactions
    def suspicious_operations(self) -> list[dict]:
        result = []
        for entry in self.analyzer._risk_history:
            if entry["risk"] in (RiskAnalyzer.RISK_MEDIUM, RiskAnalyzer.RISK_HIGH):
                result.append(entry)
        return result

    # 2) risk profile by sender (account)
    def client_risk_profile(self, sender_id: str) -> dict:
        low = medium = high = blocked = 0

        for entry in self.analyzer._risk_history:
            if entry["sender_id"] != sender_id:
                continue
            if entry["risk"] == RiskAnalyzer.RISK_LOW:
                low += 1
            elif entry["risk"] == RiskAnalyzer.RISK_MEDIUM:
                medium += 1
            elif entry["risk"] == RiskAnalyzer.RISK_HIGH:
                high += 1
                blocked += 1

        return {
            "sender_id": sender_id,
            "low": low,
            "medium": medium,
            "high": high,
            "blocked": blocked
        }

    # 3) static errors
    def error_status(self) -> dict:
        errors = self.audit_log.filter(level=AuditLog.LEVEL_ERROR)
        critical = self.audit_log.filter(level=AuditLog.LEVEL_CRITICAL)

        return {
            "error_count": len(errors),
            "critical_count": len(critical),
            "erros": errors,
            "critical": critical
        }
