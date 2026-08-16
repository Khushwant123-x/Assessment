"""
Conflict resolution engine for temporal RAG system.
Applies deterministic rules to resolve conflicts between facts.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from conflict_detection import Conflict, Fact, ConflictType


class ResolutionStrategy(Enum):
    """Strategies used to resolve conflicts."""
    SOURCE_RELIABILITY = "source_reliability"  # Prefer higher reliability source
    TEMPORAL_RECENCY = "temporal_recency"  # Prefer most recent fact
    INTERNAL_CONSISTENCY = "internal_consistency"  # Maintain consistency
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"  # Cannot resolve


@dataclass
class Resolution:
    """Represents a resolution decision for a conflict."""
    conflict_id: str
    resolution_strategy: ResolutionStrategy
    accepted_fact: Optional[Fact]  # Fact that was accepted (None if insufficient evidence)
    rejected_facts: List[Fact]  # Facts that were rejected
    confidence_score: float  # 0-1, how confident in this resolution
    explanation: str  # Human-readable explanation
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d["resolution_strategy"] = self.resolution_strategy.value
        if self.accepted_fact:
            d["accepted_fact"] = asdict(self.accepted_fact)
        d["rejected_facts"] = [asdict(f) for f in self.rejected_facts]
        return d


class ConflictResolver:
    """Resolves conflicts between facts using deterministic rules."""
    
    def __init__(self):
        """Initialize the conflict resolver."""
        self.resolutions: Dict[str, Resolution] = {}
    
    def resolve_conflict(self, conflict: Conflict) -> Resolution:
        """
        Resolve a single conflict using deterministic rules.
        
        Resolution priority order:
        1. Prefer higher source reliability (PDF > YouTube > text)
        2. If equal reliability, prefer most recent temporal marker
        3. If no temporal info, reject both (insufficient evidence)
        
        Args:
            conflict: Conflict object to resolve
            
        Returns:
            Resolution object with decision
        """
        facts = conflict.facts_involved
        
        # Handle different conflict types
        if conflict.conflict_type == ConflictType.INTERNAL_INCONSISTENCY:
            # For internal inconsistencies, reject both
            resolution = Resolution(
                conflict_id=conflict.conflict_id,
                resolution_strategy=ResolutionStrategy.INSUFFICIENT_EVIDENCE,
                accepted_fact=None,
                rejected_facts=facts,
                confidence_score=0.0,
                explanation="Internal inconsistency detected. Cannot accept either fact."
            )
            self.resolutions[conflict.conflict_id] = resolution
            return resolution
        
        if conflict.conflict_type == ConflictType.DIRECT_CONTRADICTION:
            return self._resolve_direct_contradiction(conflict)
        
        if conflict.conflict_type == ConflictType.TEMPORAL_CONFLICT:
            return self._resolve_temporal_conflict(conflict)
        
        # Default: insufficient evidence
        resolution = Resolution(
            conflict_id=conflict.conflict_id,
            resolution_strategy=ResolutionStrategy.INSUFFICIENT_EVIDENCE,
            accepted_fact=None,
            rejected_facts=facts,
            confidence_score=0.3,
            explanation="Unknown conflict type. Insufficient evidence."
        )
        self.resolutions[conflict.conflict_id] = resolution
        return resolution
    
    def _resolve_direct_contradiction(self, conflict: Conflict) -> Resolution:
        """Resolve direct contradictions using source reliability first."""
        facts = sorted(
            conflict.facts_involved,
            key=lambda f: f.reliability_score,
            reverse=True
        )
        
        # If different reliability scores, choose the more reliable
        if facts[0].reliability_score > facts[1].reliability_score:
            accepted_fact = facts[0]
            confidence = facts[0].reliability_score
            explanation = f"Accepted fact from {accepted_fact.source_name} (reliability: {confidence:.2f}) over {facts[1].source_name}"
        
        # If same reliability, use temporal information
        elif facts[0].temporal_markers and facts[1].temporal_markers:
            # Compare temporal markers
            dates1 = [m for m in facts[0].temporal_markers if self._is_date(m)]
            dates2 = [m for m in facts[1].temporal_markers if self._is_date(m)]
            
            if dates1 and dates2:
                latest_date1 = max(dates1)
                latest_date2 = max(dates2)
                
                if latest_date1 > latest_date2:
                    accepted_fact = facts[0]
                    confidence = 0.8
                    explanation = f"Accepted more recent fact from {accepted_fact.source_name} ({latest_date1}) over {facts[1].source_name} ({latest_date2})"
                else:
                    accepted_fact = facts[1]
                    confidence = 0.8
                    explanation = f"Accepted more recent fact from {accepted_fact.source_name} ({latest_date2}) over {facts[0].source_name} ({latest_date1})"
            else:
                # No temporal info, insufficient evidence
                return Resolution(
                    conflict_id=conflict.conflict_id,
                    resolution_strategy=ResolutionStrategy.INSUFFICIENT_EVIDENCE,
                    accepted_fact=None,
                    rejected_facts=facts,
                    confidence_score=0.2,
                    explanation="Insufficient evidence: same reliability and no temporal markers"
                )
        else:
            # No temporal info and same reliability, insufficient evidence
            return Resolution(
                conflict_id=conflict.conflict_id,
                resolution_strategy=ResolutionStrategy.INSUFFICIENT_EVIDENCE,
                accepted_fact=None,
                rejected_facts=facts,
                confidence_score=0.2,
                explanation="Insufficient evidence: contradictory facts with same reliability and no temporal info"
            )
        
        resolution = Resolution(
            conflict_id=conflict.conflict_id,
            resolution_strategy=ResolutionStrategy.SOURCE_RELIABILITY if confidence > 0.8 else ResolutionStrategy.TEMPORAL_RECENCY,
            accepted_fact=accepted_fact,
            rejected_facts=[f for f in facts if f.fact_id != accepted_fact.fact_id],
            confidence_score=confidence,
            explanation=explanation
        )
        
        self.resolutions[conflict.conflict_id] = resolution
        return resolution
    
    def _resolve_temporal_conflict(self, conflict: Conflict) -> Resolution:
        """Resolve temporal conflicts by choosing the most recent fact."""
        facts = conflict.facts_involved
        
        # Extract dates from temporal markers
        dates_by_fact = {}
        for fact in facts:
            dates = [m for m in fact.temporal_markers if self._is_date(m)]
            dates_by_fact[fact.fact_id] = max(dates) if dates else None
        
        # Find fact with most recent date
        facts_with_dates = [f for f in facts if dates_by_fact[f.fact_id] is not None]
        
        if facts_with_dates:
            accepted_fact = max(facts_with_dates, key=lambda f: dates_by_fact[f.fact_id])
            confidence = 0.85
            latest_date = dates_by_fact[accepted_fact.fact_id]
            explanation = f"Accepted most recent fact from {accepted_fact.source_name} dated {latest_date}"
            strategy = ResolutionStrategy.TEMPORAL_RECENCY
        else:
            # No temporal info, fall back to source reliability
            facts_by_reliability = sorted(facts, key=lambda f: f.reliability_score, reverse=True)
            accepted_fact = facts_by_reliability[0]
            confidence = accepted_fact.reliability_score
            explanation = f"No temporal markers found. Accepted based on source reliability ({accepted_fact.source_name})"
            strategy = ResolutionStrategy.SOURCE_RELIABILITY
        
        resolution = Resolution(
            conflict_id=conflict.conflict_id,
            resolution_strategy=strategy,
            accepted_fact=accepted_fact,
            rejected_facts=[f for f in facts if f.fact_id != accepted_fact.fact_id],
            confidence_score=confidence,
            explanation=explanation
        )
        
        self.resolutions[conflict.conflict_id] = resolution
        return resolution
    
    def resolve_all_conflicts(self, conflicts: List[Conflict]) -> List[Resolution]:
        """
        Resolve multiple conflicts.
        
        Args:
            conflicts: List of Conflict objects
            
        Returns:
            List of Resolution objects
        """
        resolutions = []
        for conflict in conflicts:
            resolution = self.resolve_conflict(conflict)
            resolutions.append(resolution)
        
        return resolutions
    
    def get_accepted_facts(self) -> List[Fact]:
        """Get all facts that were accepted in resolutions."""
        return [res.accepted_fact for res in self.resolutions.values() if res.accepted_fact]
    
    def get_rejected_facts(self) -> List[Fact]:
        """Get all facts that were rejected in resolutions."""
        rejected = []
        for res in self.resolutions.values():
            rejected.extend(res.rejected_facts)
        return rejected
    
    def get_resolution_statistics(self) -> Dict:
        """Get statistics about resolutions."""
        strategies_count = {}
        for res in self.resolutions.values():
            strategy = res.resolution_strategy.value
            strategies_count[strategy] = strategies_count.get(strategy, 0) + 1
        
        total_resolutions = len(self.resolutions)
        avg_confidence = sum(r.confidence_score for r in self.resolutions.values()) / max(1, total_resolutions)
        
        return {
            "total_resolutions": total_resolutions,
            "strategies_used": strategies_count,
            "average_confidence": avg_confidence,
            "accepted_facts": len([r for r in self.resolutions.values() if r.accepted_fact]),
            "insufficient_evidence": strategies_count.get("insufficient_evidence", 0)
        }
    
    def _is_date(self, marker: str) -> bool:
        """Check if a marker is a date (year)."""
        try:
            year = int(marker)
            return 1800 <= year <= 2100
        except (ValueError, TypeError):
            return False
    
    def clear_resolutions(self):
        """Clear all resolutions."""
        self.resolutions = {}
