from typing import Any, Dict
from app.schemas.prospect_score import ProspectScore
class ProspectRankingEngine:
    def _determine_grade(self, score: int) -> str:
        if score >= 85: return "A"
        if score >= 70: return "B"
        if score >= 50: return "C"
        return "D"
    def _calculate_confidence(self, company_data: Dict[str, Any]) -> int:
        confidence = 40
        if company_data.get("industry") and company_data.get("industry") != "Unknown": confidence += 15
        if company_data.get("employee_count"): confidence += 15
        if company_data.get("technologies"): confidence += 15
        if company_data.get("domain"): confidence += 15
        return min(100, confidence)
    def calculate_score(self, matrix: Dict[str, Any], company_data: Dict[str, Any]) -> ProspectScore:
        icp_fit = matrix.get("icp_fit", 0) * 0.40
        buying_signals = matrix.get("buying_signals", 0) * 0.25
        company_size = matrix.get("company_size", 0) * 0.15
        tech_fit = matrix.get("tech_fit", 0) * 0.10
        freshness = matrix.get("freshness", 0) * 0.10
        total_score = int(icp_fit + buying_signals + company_size + tech_fit + freshness)
        grade = self._determine_grade(total_score)
        reasons = []
        if icp_fit >= 30: reasons.append("Strong ICP alignment.")
        if tech_fit >= 8: reasons.append("Identified key technology overlaps.")
        if buying_signals >= 15: reasons.append("Active intent signals detected.")
        return ProspectScore(score=total_score, grade=grade, reasons=reasons, confidence=self._calculate_confidence(company_data))
