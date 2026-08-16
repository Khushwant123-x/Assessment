"""
Conflict detection engine for temporal RAG system.
Detects contradictions and conflicts between facts from different sources.
"""

from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from ingestion_pipeline import Document


class ConflictType(Enum):
    """Types of conflicts that can be detected."""
    DIRECT_CONTRADICTION = "direct_contradiction"  # "A is X" vs "A is Y"
    TEMPORAL_CONFLICT = "temporal_conflict"  # Different facts at different times
    INTERNAL_INCONSISTENCY = "internal_inconsistency"  # Contradictions within same source
    MISSING_CONTEXT = "missing_context"  # Insufficient info to resolve


@dataclass
class Fact:
    """Represents an extracted fact from a document."""
    fact_id: str
    text: str  # The fact statement
    doc_id: str  # Source document ID
    source_type: str  # "pdf", "youtube", or "text"
    source_name: str  # Human-readable source name
    timestamp: str  # When the fact was extracted
    reliability_score: float  # Source reliability (0-1)
    temporal_markers: List[str] = field(default_factory=list)  # ["2020", "January", etc.]


@dataclass
class Conflict:
    """Represents a detected conflict between facts."""
    conflict_id: str
    conflict_type: ConflictType
    facts_involved: List[Fact]  # Facts in conflict
    description: str  # Human-readable description
    severity: str  # "high", "medium", "low"
    resolution_needed: bool  # Whether this needs manual resolution
    timestamp: str = None  # When conflict was detected
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d["conflict_type"] = self.conflict_type.value
        d["facts_involved"] = [asdict(f) for f in self.facts_involved]
        return d


class ConflictDetector:
    """Detects conflicts between facts from multiple sources."""
    
    # Keywords that often indicate contradictions
    CONTRADICTION_PATTERNS = {
        "is_vs_not": [
            ("is a", "is not a"),
            ("was", "was not"),
            ("does", "does not"),
            ("did", "did not"),
        ],
        "opposite_states": [
            ("alive", "dead"),
            ("married", "single"),
            ("employed", "unemployed"),
            ("doctor", "lawyer"),
            ("student", "teacher"),
        ]
    }
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        Initialize conflict detector.
        
        Args:
            similarity_threshold: Threshold for considering facts similar (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.conflicts: List[Conflict] = []
        self.facts_cache: Dict[str, Fact] = {}
    
    def extract_facts_from_documents(self, documents: List[Document]) -> List[Fact]:
        """
        Extract facts from a list of documents.
        
        For MVP, we use simple heuristics to identify fact-like sentences.
        Advanced implementations would use NER/NLP models.
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of extracted Fact objects
        """
        facts = []
        
        for doc in documents:
            # Simple fact extraction: sentences that contain subjects and predicates
            sentences = doc.content.split('. ')
            
            for sent_idx, sentence in enumerate(sentences):
                sentence = sentence.strip()
                
                # Skip very short or empty sentences
                if len(sentence) < 20:
                    continue
                
                # Skip generic sentences
                if any(skip in sentence.lower() for skip in ["the", "there is", "you"]):
                    if len(sentence.split()) < 5:
                        continue
                
                # Extract temporal markers (years, months, etc.)
                temporal_markers = self._extract_temporal_markers(sentence)
                
                # Create fact
                fact_id = self._generate_fact_id(doc.id, sent_idx)
                fact = Fact(
                    fact_id=fact_id,
                    text=sentence,
                    doc_id=doc.id,
                    source_type=doc.source_type,
                    source_name=doc.source_name,
                    timestamp=doc.timestamp,
                    reliability_score=doc.reliability_score,
                    temporal_markers=temporal_markers
                )
                
                facts.append(fact)
                self.facts_cache[fact_id] = fact
        
        return facts
    
    def detect_conflicts(self, facts: List[Fact]) -> List[Conflict]:
        """
        Detect conflicts between facts.
        
        Args:
            facts: List of Fact objects
            
        Returns:
            List of Conflict objects
        """
        detected_conflicts = []
        
        # Compare each pair of facts
        for i, fact1 in enumerate(facts):
            for fact2 in facts[i+1:]:
                # Skip if same source
                if fact1.doc_id == fact2.doc_id:
                    continue
                
                conflict = self._compare_facts(fact1, fact2)
                
                if conflict:
                    # Check if we already have this conflict
                    if not self._conflict_exists(conflict, detected_conflicts):
                        detected_conflicts.append(conflict)
        
        self.conflicts.extend(detected_conflicts)
        return detected_conflicts
    
    def _compare_facts(self, fact1: Fact, fact2: Fact) -> Optional[Conflict]:
        """Compare two facts and detect if they conflict."""
        # Check for direct contradictions
        if self._is_direct_contradiction(fact1.text, fact2.text):
            conflict = Conflict(
                conflict_id=self._generate_conflict_id(fact1.fact_id, fact2.fact_id),
                conflict_type=ConflictType.DIRECT_CONTRADICTION,
                facts_involved=[fact1, fact2],
                description=f"Direct contradiction between sources: '{fact1.text[:50]}...' (from {fact1.source_name}) vs '{fact2.text[:50]}...' (from {fact2.source_name})",
                severity="high",
                resolution_needed=True
            )
            return conflict
        
        # Check for temporal conflicts
        if self._is_temporal_conflict(fact1, fact2):
            conflict = Conflict(
                conflict_id=self._generate_conflict_id(fact1.fact_id, fact2.fact_id),
                conflict_type=ConflictType.TEMPORAL_CONFLICT,
                facts_involved=[fact1, fact2],
                description=f"Temporal conflict: fact changes over time between sources",
                severity="medium",
                resolution_needed=True
            )
            return conflict
        
        return None
    
    def _is_direct_contradiction(self, text1: str, text2: str) -> bool:
        """Check if two fact texts directly contradict each other."""
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        # Extract subject (simple heuristic: first noun/entity)
        subject1 = self._extract_subject(text1_lower)
        subject2 = self._extract_subject(text2_lower)
        
        # Must have same subject to contradict
        if subject1 != subject2:
            return False
        
        # Check for opposite predicates
        for pos, neg in self.CONTRADICTION_PATTERNS["opposite_states"]:
            if (pos in text1_lower and neg in text2_lower) or \
               (neg in text1_lower and pos in text2_lower):
                return True
        
        # Check for "is" vs "is not" patterns
        for pos, neg in self.CONTRADICTION_PATTERNS["is_vs_not"]:
            if (pos in text1_lower and neg in text2_lower) or \
               (neg in text1_lower and pos in text2_lower):
                # Additional check: must have same entity
                if self._extract_entity(text1_lower) == self._extract_entity(text2_lower):
                    return True
        
        return False
    
    def _is_temporal_conflict(self, fact1: Fact, fact2: Fact) -> bool:
        """Check if two facts have temporal conflicts (different times, different states)."""
        # Must have temporal markers in both
        if not fact1.temporal_markers or not fact2.temporal_markers:
            return False
        
        # If temporal markers differ, it might be temporal conflict
        # (same entity, different states at different times)
        return self._is_direct_contradiction(fact1.text, fact2.text)
    
    def _extract_temporal_markers(self, text: str) -> List[str]:
        """Extract temporal markers from text (years, months, etc.)."""
        markers = []
        
        # Year patterns (1900-2099)
        import re
        years = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        markers.extend(years)
        
        # Month patterns
        months = ["january", "february", "march", "april", "may", "june",
                  "july", "august", "september", "october", "november", "december"]
        text_lower = text.lower()
        for month in months:
            if month in text_lower:
                markers.append(month)
        
        # Relative time
        relative_times = ["recently", "now", "currently", "before", "after", "earlier", "later"]
        for rt in relative_times:
            if rt in text_lower:
                markers.append(rt)
        
        return markers
    
    def _extract_subject(self, text: str) -> Optional[str]:
        """Extract the subject of a sentence (simple heuristic)."""
        # Get the first word or first capitalized word
        words = text.split()
        
        for word in words[:5]:  # Check first 5 words
            word_clean = word.strip('.,;:!?')
            if len(word_clean) > 2:
                return word_clean.lower()
        
        return None
    
    def _extract_entity(self, text: str) -> Optional[str]:
        """Extract named entity from text (simple heuristic)."""
        # Look for capitalized words or proper nouns
        words = text.split()
        for word in words[:8]:
            word_clean = word.strip('.,;:!?')
            if len(word_clean) > 2 and (word_clean[0].isupper() or word_clean in ["john", "john", "mary"]):
                return word_clean.lower()
        
        return self._extract_subject(text)
    
    def _generate_fact_id(self, doc_id: str, sentence_idx: int) -> str:
        """Generate a unique ID for a fact."""
        return f"{doc_id}_sent_{sentence_idx}"
    
    def _generate_conflict_id(self, fact_id1: str, fact_id2: str) -> str:
        """Generate a unique ID for a conflict."""
        sorted_ids = tuple(sorted([fact_id1, fact_id2]))
        import hashlib
        return hashlib.md5(f"{sorted_ids}".encode()).hexdigest()[:12]
    
    def _conflict_exists(self, conflict: Conflict, conflicts: List[Conflict]) -> bool:
        """Check if a conflict already exists in the list."""
        for existing in conflicts:
            if (existing.facts_involved[0].fact_id == conflict.facts_involved[0].fact_id and
                existing.facts_involved[1].fact_id == conflict.facts_involved[1].fact_id):
                return True
        
        return False
    
    def get_conflicts_by_severity(self, severity: str) -> List[Conflict]:
        """Get conflicts filtered by severity level."""
        return [c for c in self.conflicts if c.severity == severity]
    
    def get_high_priority_conflicts(self) -> List[Conflict]:
        """Get high-severity conflicts that need resolution."""
        return [c for c in self.conflicts if c.severity == "high" and c.resolution_needed]
    
    def clear_conflicts(self):
        """Clear all detected conflicts."""
        self.conflicts = []
