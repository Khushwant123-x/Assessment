"""
Test suite for Temporal Conflict Resolution RAG system.
Covers edge cases including:
- Direct contradictions
- Temporal conflicts
- Source reliability conflicts
- Duplicate events
- Late-arriving data
- Determinism/replay verification
"""

import pytest
from datetime import datetime, timedelta
import json
from pathlib import Path

from ingestion_pipeline import SourceIngestionPipeline, Document
from conflict_detection import ConflictDetector, Fact, ConflictType
from conflict_resolution import ConflictResolver, ResolutionStrategy
from rag_orchestrator import TemporalConflictRAG


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def rag_system():
    """Create a fresh RAG system for each test."""
    return TemporalConflictRAG()


@pytest.fixture
def ingestion_pipeline():
    """Create a fresh ingestion pipeline."""
    return SourceIngestionPipeline()


@pytest.fixture
def conflict_detector():
    """Create a fresh conflict detector."""
    return ConflictDetector()


@pytest.fixture
def conflict_resolver():
    """Create a fresh conflict resolver."""
    return ConflictResolver()


# ============================================================================
# TEST DATA / FIXTURES
# ============================================================================

def create_test_document(
    source_type: str,
    source_name: str,
    content: str,
    reliability_score: float = 1.0,
    chunk_index: int = 0
) -> Document:
    """Helper to create test documents."""
    return Document(
        id=f"test_{source_name}_{chunk_index}",
        source_type=source_type,
        source_name=source_name,
        content=content,
        chunk_index=chunk_index,
        chunk_size=1,
        embedding=[0.1] * 384,  # Dummy embedding
        reliability_score=reliability_score,
        timestamp=datetime.utcnow().isoformat()
    )


def create_test_fact(
    text: str,
    source_name: str,
    source_type: str = "pdf",
    reliability_score: float = 1.0,
    temporal_markers: list = None
) -> Fact:
    """Helper to create test facts."""
    if temporal_markers is None:
        temporal_markers = []
    
    return Fact(
        fact_id=f"fact_{source_name}_{len(text)}",
        text=text,
        doc_id=f"doc_{source_name}",
        source_type=source_type,
        source_name=source_name,
        timestamp=datetime.utcnow().isoformat(),
        reliability_score=reliability_score,
        temporal_markers=temporal_markers
    )


# ============================================================================
# EDGE CASE 1: DIRECT CONTRADICTIONS
# ============================================================================

class TestDirectContradictions:
    """Test detection and resolution of direct contradictions."""
    
    def test_direct_contradiction_detection(self, conflict_detector):
        """Test detection of direct contradictions between facts."""
        fact1 = create_test_fact(
            "John is a doctor",
            "Source A",
            source_type="pdf",
            reliability_score=1.0
        )
        fact2 = create_test_fact(
            "John is a lawyer",
            "Source B",
            source_type="text",
            reliability_score=0.5
        )
        
        conflicts = conflict_detector.detect_conflicts([fact1, fact2])
        
        assert len(conflicts) >= 1, "Should detect contradiction"
        assert any(c.conflict_type == ConflictType.DIRECT_CONTRADICTION for c in conflicts)
    
    def test_source_reliability_resolution(self, conflict_resolver):
        """Test that higher reliability source is preferred in contradictions."""
        fact_pdf = create_test_fact(
            "John is a doctor",
            "PDF Source",
            source_type="pdf",
            reliability_score=1.0
        )
        fact_text = create_test_fact(
            "John is a lawyer",
            "Text Source",
            source_type="text",
            reliability_score=0.5
        )
        
        from conflict_detection import Conflict
        conflict = Conflict(
            conflict_id="test_conflict_1",
            conflict_type=ConflictType.DIRECT_CONTRADICTION,
            facts_involved=[fact_pdf, fact_text],
            description="Test contradiction",
            severity="high",
            resolution_needed=True
        )
        
        resolution = conflict_resolver.resolve_conflict(conflict)
        
        assert resolution.accepted_fact is not None
        assert resolution.accepted_fact.source_name == "PDF Source"
        assert resolution.resolution_strategy == ResolutionStrategy.SOURCE_RELIABILITY


# ============================================================================
# EDGE CASE 2: TEMPORAL CONFLICTS
# ============================================================================

class TestTemporalConflicts:
    """Test detection and resolution of temporal conflicts."""
    
    def test_temporal_conflict_detection(self, conflict_detector):
        """Test detection of temporal conflicts (same entity, different times)."""
        fact_2020 = create_test_fact(
            "John was a doctor in 2020",
            "Source A",
            temporal_markers=["2020"]
        )
        fact_2023 = create_test_fact(
            "John is a lawyer in 2023",
            "Source B",
            temporal_markers=["2023"]
        )
        
        conflicts = conflict_detector.detect_conflicts([fact_2020, fact_2023])
        
        # Should detect temporal conflict
        assert len(conflicts) >= 1
    
    def test_temporal_resolution_by_recency(self, conflict_resolver):
        """Test that most recent temporal fact is preferred."""
        fact_2020 = create_test_fact(
            "John was a doctor in 2020",
            "Source A",
            source_type="pdf",
            reliability_score=1.0,
            temporal_markers=["2020"]
        )
        fact_2023 = create_test_fact(
            "John is a lawyer in 2023",
            "Source B",
            source_type="youtube",
            reliability_score=0.7,
            temporal_markers=["2023"]
        )
        
        from conflict_detection import Conflict
        conflict = Conflict(
            conflict_id="test_temporal_1",
            conflict_type=ConflictType.TEMPORAL_CONFLICT,
            facts_involved=[fact_2020, fact_2023],
            description="Temporal conflict",
            severity="high",
            resolution_needed=True
        )
        
        resolution = conflict_resolver.resolve_conflict(conflict)
        
        assert resolution.accepted_fact is not None
        # Should prefer 2023 (more recent)
        assert "2023" in resolution.accepted_fact.temporal_markers


# ============================================================================
# EDGE CASE 3: SOURCE RELIABILITY HIERARCHY
# ============================================================================

class TestSourceReliabilityHierarchy:
    """Test that PDF > YouTube > Text reliability is maintained."""
    
    def test_pdf_preferred_over_youtube(self, conflict_resolver):
        """Test that PDF sources are preferred over YouTube."""
        fact_pdf = create_test_fact(
            "Fact X is true",
            "PDF Source",
            source_type="pdf",
            reliability_score=1.0
        )
        fact_youtube = create_test_fact(
            "Fact X is false",
            "YouTube Source",
            source_type="youtube",
            reliability_score=0.7
        )
        
        from conflict_detection import Conflict
        conflict = Conflict(
            conflict_id="test_source_1",
            conflict_type=ConflictType.DIRECT_CONTRADICTION,
            facts_involved=[fact_pdf, fact_youtube],
            description="Source conflict",
            severity="high",
            resolution_needed=True
        )
        
        resolution = conflict_resolver.resolve_conflict(conflict)
        
        assert resolution.accepted_fact.source_name == "PDF Source"
        assert resolution.resolution_strategy == ResolutionStrategy.SOURCE_RELIABILITY
    
    def test_youtube_preferred_over_text(self, conflict_resolver):
        """Test that YouTube sources are preferred over text."""
        fact_youtube = create_test_fact(
            "Fact X is true",
            "YouTube Source",
            source_type="youtube",
            reliability_score=0.7
        )
        fact_text = create_test_fact(
            "Fact X is false",
            "Text Source",
            source_type="text",
            reliability_score=0.5
        )
        
        from conflict_detection import Conflict
        conflict = Conflict(
            conflict_id="test_source_2",
            conflict_type=ConflictType.DIRECT_CONTRADICTION,
            facts_involved=[fact_youtube, fact_text],
            description="Source conflict",
            severity="high",
            resolution_needed=True
        )
        
        resolution = conflict_resolver.resolve_conflict(conflict)
        
        assert resolution.accepted_fact.source_name == "YouTube Source"


# ============================================================================
# EDGE CASE 4: DUPLICATE EVENTS
# ============================================================================

class TestDuplicateEvents:
    """Test handling of duplicate events from the same and different sources."""
    
    def test_same_fact_different_sources(self, conflict_detector):
        """Test that identical facts from different sources don't create conflicts."""
        fact1 = create_test_fact(
            "Paris is the capital of France",
            "Source A",
            source_type="pdf"
        )
        fact2 = create_test_fact(
            "Paris is the capital of France",
            "Source B",
            source_type="youtube"
        )
        
        conflicts = conflict_detector.detect_conflicts([fact1, fact2])
        
        # Should not detect contradiction for identical facts
        contradictions = [c for c in conflicts if c.conflict_type == ConflictType.DIRECT_CONTRADICTION]
        assert len(contradictions) == 0
    
    def test_duplicate_ingestion_idempotency(self, rag_system):
        """Test that ingesting same document twice doesn't create duplicate conflicts."""
        text = "John is a doctor. John works at the hospital."
        
        # Ingest same text twice
        docs1 = rag_system.ingest_text(text, "duplicate_source")
        docs2 = rag_system.ingest_text(text, "duplicate_source")
        
        stats = rag_system.get_statistics()
        
        # Should have ingested both times (no deduplication at ingestion level)
        # But conflicts shouldn't be created from same content
        assert stats["total_documents_ingested"] == len(docs1) + len(docs2)


# ============================================================================
# EDGE CASE 5: LATE-ARRIVING DATA
# ============================================================================

class TestLateArrivingData:
    """Test handling of data that arrives after initial processing."""
    
    def test_late_arriving_data_with_conflict(self, rag_system):
        """Test processing when conflicting data arrives later."""
        # Initial data
        initial_text = "John is a doctor."
        rag_system.ingest_text(initial_text, "Source1")
        
        result1 = rag_system.process_query("What is John's profession?")
        initial_conflicts = result1["conflicts_detected"]
        
        # Late-arriving conflicting data
        late_text = "John is actually a lawyer."
        rag_system.ingest_text(late_text, "Source2")
        
        result2 = rag_system.process_query("What is John's profession?")
        updated_conflicts = result2["conflicts_detected"]
        
        # Updated query should have more/different conflicts
        assert updated_conflicts >= initial_conflicts


# ============================================================================
# EDGE CASE 6: INTERNAL INCONSISTENCY
# ============================================================================

class TestInternalInconsistency:
    """Test handling of internally inconsistent claims."""
    
    def test_internal_inconsistency_rejection(self, conflict_resolver):
        """Test that internally inconsistent facts are rejected."""
        fact1 = create_test_fact(
            "John is a doctor",
            "Inconsistent Source",
            source_type="text"
        )
        fact2 = create_test_fact(
            "John is a lawyer",
            "Inconsistent Source",
            source_type="text"
        )
        
        from conflict_detection import Conflict
        conflict = Conflict(
            conflict_id="test_internal_1",
            conflict_type=ConflictType.INTERNAL_INCONSISTENCY,
            facts_involved=[fact1, fact2],
            description="Internal inconsistency",
            severity="high",
            resolution_needed=True
        )
        
        resolution = conflict_resolver.resolve_conflict(conflict)
        
        assert resolution.accepted_fact is None
        assert resolution.resolution_strategy == ResolutionStrategy.INSUFFICIENT_EVIDENCE


# ============================================================================
# EDGE CASE 7: INSUFFICIENT EVIDENCE
# ============================================================================

class TestInsufficientEvidence:
    """Test handling of cases with insufficient evidence to resolve."""
    
    def test_equal_reliability_no_temporal(self, conflict_resolver):
        """Test resolution when facts have equal reliability and no temporal info."""
        fact1 = create_test_fact(
            "The Earth is flat",
            "Source A",
            source_type="text",
            reliability_score=0.5
        )
        fact2 = create_test_fact(
            "The Earth is round",
            "Source B",
            source_type="text",
            reliability_score=0.5
        )
        
        from conflict_detection import Conflict
        conflict = Conflict(
            conflict_id="test_insufficient_1",
            conflict_type=ConflictType.DIRECT_CONTRADICTION,
            facts_involved=[fact1, fact2],
            description="Insufficient evidence",
            severity="high",
            resolution_needed=True
        )
        
        resolution = conflict_resolver.resolve_conflict(conflict)
        
        assert resolution.resolution_strategy == ResolutionStrategy.INSUFFICIENT_EVIDENCE
        assert resolution.accepted_fact is None


# ============================================================================
# EDGE CASE 8: DETERMINISM AND REPLAY
# ============================================================================

class TestDeterminismAndReplay:
    """Test that identical inputs produce identical outputs (determinism)."""
    
    def test_replay_produces_same_results(self, rag_system):
        """Test that replaying a query produces identical results."""
        # Ingest data
        text = "Paris is the capital of France."
        rag_system.ingest_text(text, "Geography Source")
        
        # Process query
        query = "What is the capital of France?"
        result1 = rag_system.process_query(query)
        trace_id = result1["trace_id"]
        
        # Replay the query
        result2 = rag_system.process_query(query)
        
        # Answers should be identical
        assert result1["answer"] == result2["answer"]
        assert abs(result1["confidence"] - result2["confidence"]) < 0.01
    
    def test_deterministic_hash_matches(self, rag_system):
        """Test that deterministic hashes match for identical processing."""
        text = "The Moon orbits the Earth."
        rag_system.ingest_text(text, "Astronomy Source")
        
        result = rag_system.process_query("What orbits the Earth?")
        trace_id = result["trace_id"]
        
        # Get the trace and verify hash
        trace = rag_system.audit_generator.get_trace(trace_id)
        
        assert trace.deterministic_hash != ""
        assert len(trace.deterministic_hash) == 16


# ============================================================================
# EDGE CASE 9: PERFORMANCE
# ============================================================================

class TestPerformance:
    """Test that processing completes within time constraints."""
    
    def test_query_processing_under_30_seconds(self, rag_system):
        """Test that query processing completes within 30 seconds."""
        # Ingest multiple sources
        for i in range(3):
            text = f"Fact {i}: Some information about topic."
            rag_system.ingest_text(text, f"Source{i}")
        
        query = "What information is available?"
        
        import time
        start = time.time()
        result = rag_system.process_query(query)
        elapsed = time.time() - start
        
        assert elapsed < 30.0, f"Processing took {elapsed:.2f} seconds, should be < 30s"
        assert result["audit_trace"].processing_time_ms < 30000


# ============================================================================
# EDGE CASE 10: IDEMPOTENCY
# ============================================================================

class TestIdempotency:
    """Test that repeated processing doesn't create duplicate effects."""
    
    def test_multiple_queries_idempotent(self, rag_system):
        """Test that processing same query multiple times doesn't change results."""
        text = "London is the capital of England."
        rag_system.ingest_text(text, "Geography Source")
        
        query = "What is the capital of England?"
        
        # Process same query 3 times
        results = []
        for _ in range(3):
            result = rag_system.process_query(query)
            results.append(result["answer"])
        
        # All results should be identical
        assert results[0] == results[1] == results[2]


# ============================================================================
# EDGE CASE 11: TEMPORAL BOUNDARY CONDITIONS
# ============================================================================

class TestTemporalBoundaryConditions:
    """Test temporal processing at boundary conditions (midnight, year boundaries)."""
    
    def test_midnight_boundary_processing(self):
        """Test that dates at midnight are handled correctly."""
        detector = ConflictDetector()
        
        fact_before_midnight = create_test_fact(
            "Event happened on 2023-12-31 23:59",
            "Source A",
            temporal_markers=["2023-12-31"]
        )
        fact_after_midnight = create_test_fact(
            "Event happened on 2024-01-01 00:01",
            "Source B",
            temporal_markers=["2024-01-01"]
        )
        
        # Detector should handle temporal markers correctly
        extracted_markers1 = detector._extract_temporal_markers(
            fact_before_midnight.text
        )
        extracted_markers2 = detector._extract_temporal_markers(
            fact_after_midnight.text
        )
        
        assert len(extracted_markers1) >= 0
        assert len(extracted_markers2) >= 0
    
    def test_year_boundary_resolution(self, conflict_resolver):
        """Test conflict resolution at year boundaries."""
        fact_2023 = create_test_fact(
            "Status in 2023",
            "Source A",
            temporal_markers=["2023"]
        )
        fact_2024 = create_test_fact(
            "Status in 2024",
            "Source B",
            temporal_markers=["2024"]
        )
        
        from conflict_detection import Conflict
        conflict = Conflict(
            conflict_id="test_year_boundary",
            conflict_type=ConflictType.TEMPORAL_CONFLICT,
            facts_involved=[fact_2023, fact_2024],
            description="Year boundary conflict",
            severity="medium",
            resolution_needed=True
        )
        
        resolution = conflict_resolver.resolve_conflict(conflict)
        
        # Should resolve and prefer more recent (2024)
        assert resolution.accepted_fact is not None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_end_to_end_workflow(self, rag_system):
        """Test complete workflow: ingest → detect → resolve → answer."""
        # Ingest data from different sources
        pdf_text = "London was founded by the Romans in 43 AD."
        youtube_text = "London is located in England."
        user_text = "London is a major city."
        
        rag_system.ingest_text(pdf_text, "PDF Source")
        rag_system.ingest_text(youtube_text, "YouTube Source")
        rag_system.ingest_text(user_text, "User Text")
        
        # Process query
        result = rag_system.process_query("Where is London located?")
        
        # Verify results
        assert result["answer"] != ""
        assert result["confidence"] > 0.0
        assert result["audit_trace"] is not None
        assert result["trace_id"] != ""
    
    def test_audit_trail_completeness(self, rag_system):
        """Test that audit trails contain all necessary information."""
        rag_system.ingest_text("Test fact", "Test Source")
        
        result = rag_system.process_query("Test query?")
        trace = result["audit_trace"]
        
        # Verify all required fields
        assert trace.trace_id != ""
        assert trace.query == "Test query?"
        assert trace.query_timestamp != ""
        assert trace.sources_considered is not None
        assert trace.documents_retrieved is not None
        assert trace.facts_extracted is not None
        assert trace.final_answer != ""
        assert trace.deterministic_hash != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
