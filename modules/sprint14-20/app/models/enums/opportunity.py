from enum import Enum
class OpportunityStatus(str, Enum): NEW, GENERATING, QUALIFIED, DISQUALIFIED, ACCEPTED, REJECTED = "NEW", "GENERATING", "QUALIFIED", "DISQUALIFIED", "ACCEPTED", "REJECTED"
class OpportunityPriority(str, Enum): LOW, MEDIUM, HIGH = "LOW", "MEDIUM", "HIGH"
