"""
Auditable decision trace system for temporal RAG.
Generates comprehensive audit trails and enables replay of decisions.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import hashlib
from pathlib import Path

from ingestion_pipeline import Document
from conflict_detection import Fact, Conflict
from conflict_resolution import Resolution


@dataclass
class DecisionTrace:
    """Represents a complete decision trace for a query."""
    trace_id: str
    query: str
    query_timestamp: str
    final_answer: str
    
    # Input information
    sources_considered: List[Dict[str, Any]] = field(default_factory=list)
    documents_retrieved: List[Dict[str, Any]] = field(default_factory=list)
    
    # Processing steps
    facts_extracted: List[Dict[str, Any]] = field(default_factory=list)
    conflicts_detected: List[Dict[str, Any]] = field(default_factory=list)
    conflicts_resolved: List[Dict[str, Any]] = field(default_factory=list)
    
    # Final decision continued
    accepted_facts: List[Dict[str, Any]] = field(default_factory=list)
    rejected_facts: List[Dict[str, Any]] = field(default_factory=list)
    overall_confidence: float = 0.0
    
    # Metadata
    processing_time_ms: float = 0.0
    deterministic_hash: str = ""  # Hash for replay verification
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save_to_file(self, file_path: str):
        """Save trace to JSON file."""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(self.to_json())
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'DecisionTrace':
        """Load trace from JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls(**data)


class AuditTraceGenerator:
    """Generates comprehensive audit trails for all decisions."""
    
    def __init__(self):
        """Initialize the audit trace generator."""
        self.traces: Dict[str, DecisionTrace] = {}
    
    def create_trace(self, query: str) -> str:
        """
        Create a new decision trace.
        
        Args:
            query: The user query
            
        Returns:
            Trace ID for this query
        """
        trace_id = self._generate_trace_id(query)
        
        trace = DecisionTrace(
            trace_id=trace_id,
            query=query,
            query_timestamp=datetime.utcnow().isoformat(),
            final_answer=""
        )
        
        self.traces[trace_id] = trace
        return trace_id
    
    def record_sources_considered(
        self,
        trace_id: str,
        documents: List[Document]
    ):
        """Record which sources were considered."""
        if trace_id not in self.traces:
            return
        
        # Group documents by source
        sources_dict = {}
        for doc in documents:
            if doc.source_name not in sources_dict:
                sources_dict[doc.source_name] = {
                    "source_name": doc.source_name,
                    "source_type": doc.source_type,
                    "reliability_score": doc.reliability_score,
                    "chunk_count": 0,
                    "timestamp": doc.timestamp
                }
            sources_dict[doc.source_name]["chunk_count"] += 1
        
        self.traces[trace_id].sources_considered = list(sources_dict.values())
        self.traces[trace_id].documents_retrieved = [
            {
                "doc_id": doc.id,
                "source_type": doc.source_type,
                "source_name": doc.source_name,
                "chunk_index": doc.chunk_index,
                "timestamp": doc.timestamp,
                "content_preview": doc.content[:100] + "..." if len(doc.content) > 100 else doc.content
            }
            for doc in documents
        ]
    
    def record_facts_extracted(
        self,
        trace_id: str,
        facts: List[Fact]
    ):
        """Record extracted facts."""
        if trace_id not in self.traces:
            return
        
        self.traces[trace_id].facts_extracted = [
            {
                "fact_id": fact.fact_id,
                "text": fact.text,
                "source_name": fact.source_name,
                "source_type": fact.source_type,
                "reliability_score": fact.reliability_score,
                "temporal_markers": fact.temporal_markers,
                "timestamp": fact.timestamp
            }
            for fact in facts
        ]
    
    def record_conflicts_detected(
        self,
        trace_id: str,
        conflicts: List[Conflict]
    ):
        """Record detected conflicts."""
        if trace_id not in self.traces:
            return
        
        self.traces[trace_id].conflicts_detected = [
            {
                "conflict_id": conflict.conflict_id,
                "conflict_type": conflict.conflict_type.value,
                "severity": conflict.severity,
                "description": conflict.description,
                "facts_involved": [
                    {
                        "fact_id": f.fact_id,
                        "text": f.text,
                        "source_name": f.source_name
                    }
                    for f in conflict.facts_involved
                ],
                "resolution_needed": conflict.resolution_needed,
                "timestamp": conflict.timestamp
            }
            for conflict in conflicts
        ]
    
    def record_conflicts_resolved(
        self,
        trace_id: str,
        resolutions: List[Resolution]
    ):
        """Record conflict resolutions."""
        if trace_id not in self.traces:
            return
        
        resolved_list = []
        for resolution in resolutions:
            resolved_list.append({
                "conflict_id": resolution.conflict_id,
                "resolution_strategy": resolution.resolution_strategy.value,
                "accepted_fact": {
                    "fact_id": resolution.accepted_fact.fact_id,
                    "text": resolution.accepted_fact.text,
                    "source_name": resolution.accepted_fact.source_name
                } if resolution.accepted_fact else None,
                "rejected_facts": [
                    {
                        "fact_id": f.fact_id,
                        "text": f.text,
                        "source_name": f.source_name
                    }
                    for f in resolution.rejected_facts
                ],
                "confidence_score": resolution.confidence_score,
                "explanation": resolution.explanation,
                "timestamp": resolution.timestamp
            })
        
        self.traces[trace_id].conflicts_resolved = resolved_list
    
    def record_final_decision(
        self,
        trace_id: str,
        final_answer: str,
        accepted_facts: List[Fact],
        rejected_facts: List[Fact],
        overall_confidence: float = 0.0,
        processing_time_ms: float = 0.0
    ):
        """Record the final decision."""
        if trace_id not in self.traces:
            return
        
        self.traces[trace_id].final_answer = final_answer
        self.traces[trace_id].accepted_facts = [
            {
                "fact_id": f.fact_id,
                "text": f.text,
                "source_name": f.source_name,
                "source_type": f.source_type,
                "reliability_score": f.reliability_score
            }
            for f in accepted_facts
        ]
        self.traces[trace_id].rejected_facts = [
            {
                "fact_id": f.fact_id,
                "text": f.text,
                "source_name": f.source_name,
                "source_type": f.source_type,
                "reliability_score": f.reliability_score
            }
            for f in rejected_facts
        ]
        self.traces[trace_id].overall_confidence = overall_confidence
        self.traces[trace_id].processing_time_ms = processing_time_ms
        
        # Generate deterministic hash for replay verification
        self.traces[trace_id].deterministic_hash = self._generate_deterministic_hash(
            self.traces[trace_id]
        )
    
    def get_trace(self, trace_id: str) -> Optional[DecisionTrace]:
        """Get a decision trace."""
        return self.traces.get(trace_id)
    
    def save_trace(self, trace_id: str, file_path: str):
        """Save a trace to file."""
        if trace_id in self.traces:
            self.traces[trace_id].save_to_file(file_path)
    
    def load_trace(self, file_path: str) -> DecisionTrace:
        """Load a trace from file."""
        trace = DecisionTrace.load_from_file(file_path)
        self.traces[trace.trace_id] = trace
        return trace
    
    def get_all_traces(self) -> Dict[str, DecisionTrace]:
        """Get all traces."""
        return self.traces.copy()
    
    def export_audit_trail(self, output_dir: str = "audit_trails"):
        """Export all audit trails to JSON files."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        for trace_id, trace in self.traces.items():
            file_path = Path(output_dir) / f"{trace_id}_trace.json"
            trace.save_to_file(str(file_path))
        
        # Also create a summary file
        summary = {
            "total_traces": len(self.traces),
            "traces": [
                {
                    "trace_id": trace.trace_id,
                    "query": trace.query,
                    "timestamp": trace.query_timestamp,
                    "conflicts_detected": len(trace.conflicts_detected),
                    "conflicts_resolved": len(trace.conflicts_resolved),
                    "overall_confidence": trace.overall_confidence,
                    "processing_time_ms": trace.processing_time_ms
                }
                for trace in self.traces.values()
            ]
        }
        
        summary_path = Path(output_dir) / "summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
    
    def verify_replay_determinism(self, trace_id: str, new_trace: DecisionTrace) -> bool:
        """
        Verify that replaying produces the same results (determinism check).
        
        Args:
            trace_id: Original trace ID
            new_trace: New trace from replay
            
        Returns:
            True if results are deterministic (hashes match)
        """
        if trace_id not in self.traces:
            return False
        
        original_hash = self.traces[trace_id].deterministic_hash
        new_hash = new_trace.deterministic_hash
        
        return original_hash == new_hash
    
    def _generate_trace_id(self, query: str) -> str:
        """Generate a unique trace ID."""
        timestamp = datetime.utcnow().isoformat()
        seed = f"{query}_{timestamp}"
        return hashlib.md5(seed.encode()).hexdigest()[:16]
    
    def _generate_deterministic_hash(self, trace: DecisionTrace) -> str:
        """
        Generate a deterministic hash of the trace for replay verification.
        
        This hash is based on:
        - Query
        - Accepted facts
        - Final answer
        - Resolution strategy
        """
        # Create a stable representation
        key_data = {
            "query": trace.query,
            "final_answer": trace.final_answer,
            "accepted_facts": sorted(
                [f["fact_id"] for f in trace.accepted_facts]
            ),
            "conflicts_resolved": len(trace.conflicts_resolved),
            "overall_confidence": round(trace.overall_confidence, 3)
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]
    
    def clear_traces(self):
        """Clear all traces."""
        self.traces = {}
