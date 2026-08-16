# Test Fixtures and Edge Case Documentation

## Overview

This document describes the test fixtures and edge cases used to validate the Temporal Conflict Resolution RAG system. The system is tested against 11+ edge cases to ensure robust conflict detection and resolution.

## Edge Case Test Scenarios

### Edge Case 1: Direct Contradictions

**Description**: Two sources make directly contradictory claims about the same entity.

**Example**:
```
Query: "What is John's profession?"

Source A (PDF, reliability=1.0): "John is a certified software engineer"
Source B (Text, reliability=0.5): "John is practicing law"

Expected Behavior:
- ✓ Detect DIRECT_CONTRADICTION
- ✓ Apply SOURCE_RELIABILITY resolution (PDF > Text)
- ✓ Accept: "John is a certified software engineer"
- ✓ Confidence: 0.95
```

**Test File**: `test_rag_system.py::TestDirectContradictions`

**Related Tests**:
- `test_direct_contradiction_detection()` - Validates conflict is detected
- `test_source_reliability_resolution()` - Validates resolution logic

---

### Edge Case 2: Temporal Conflicts

**Description**: Same entity has different properties at different points in time.

**Example**:
```
Query: "What was John's career progression?"

Source A (PDF 2020, reliability=1.0): "In 2020, John was an engineer at Tech Corp"
Source B (YouTube 2024, reliability=0.7): "In 2024, John is in product management"

Expected Behavior:
- ✓ Detect TEMPORAL_CONFLICT
- ✓ Apply TEMPORAL_RECENCY resolution (2024 > 2020)
- ✓ Accept: "In 2024, John is in product management"
- ✓ Confidence: 0.85
```

**Test File**: `test_rag_system.py::TestTemporalConflicts`

**Related Tests**:
- `test_temporal_conflict_detection()` - Validates temporal marker extraction
- `test_temporal_resolution_by_recency()` - Validates most recent date is preferred

---

### Edge Case 3: Source Reliability Hierarchy

**Description**: Conflicting facts where PDF > YouTube > Text reliability.

**Example**:
```
Query: "When was the Internet invented?"

Source A (PDF, reliability=1.0): "ARPANET, 1969"
Source B (YouTube, reliability=0.7): "Web by Berners-Lee, 1989"

Expected Behavior:
- ✓ Detect DIRECT_CONTRADICTION
- ✓ Apply SOURCE_RELIABILITY (1.0 > 0.7)
- ✓ Accept: PDF source
- ✓ Confidence: 0.90
```

**Test File**: `test_rag_system.py::TestSourceReliabilityHierarchy`

**Related Tests**:
- `test_pdf_preferred_over_youtube()` - PDF > YouTube
- `test_youtube_preferred_over_text()` - YouTube > Text

---

### Edge Case 4: Duplicate Events

**Description**: Identical facts from different sources should not create conflicts.

**Example**:
```
Query: "What is the capital of France?"

Source A (PDF, reliability=1.0): "Paris is the capital of France"
Source B (YouTube, reliability=0.7): "Paris is the capital of France"

Expected Behavior:
- ✓ NO conflict detected
- ✓ Both facts accepted
- ✓ Confidence: 0.95 (high agreement)
```

**Test File**: `test_rag_system.py::TestDuplicateEvents`

**Related Tests**:
- `test_same_fact_different_sources()` - Validates identical facts don't conflict
- `test_duplicate_ingestion_idempotency()` - Validates duplicate ingestion handling

---

### Edge Case 5: Late-Arriving Data

**Description**: Conflicting data that arrives after initial processing.

**Example**:
```
Query 1: "Who is the CEO of Company X?"
Initial: "John Doe - PDF 2023, reliability=1.0"
Result: Confidence 0.95

[Later, new data arrives]

Ingest: "Jane Smith - YouTube 2024, reliability=0.7"

Query 2: "Who is the CEO of Company X?"
Now: Conflict detected (different people at different times)
Resolution: Accept Jane Smith (more recent, 2024)
Result: Confidence 0.75
```

**Test File**: `test_rag_system.py::TestLateArrivingData`

**Related Tests**:
- `test_late_arriving_data_with_conflict()` - Validates handling of late data

---

### Edge Case 6: Internal Inconsistency

**Description**: Same source contains contradictory statements.

**Example**:
```
Query: "Is Product X waterproof?"

Source (PDF, reliability=1.0) Section 1: "Product X is completely waterproof"
Source (PDF, reliability=1.0) Section 2: "Do not use Product X in water"

Expected Behavior:
- ✓ Detect INTERNAL_INCONSISTENCY
- ✓ Apply INSUFFICIENT_EVIDENCE resolution
- ✓ Accept: None
- ✓ Confidence: 0.00
- ✓ Return: "Insufficient evidence"
```

**Test File**: `test_rag_system.py::TestInternalInconsistency`

**Related Tests**:
- `test_internal_inconsistency_rejection()` - Validates conflicting facts are rejected

---

### Edge Case 7: Insufficient Evidence

**Description**: Equal reliability sources with contradictory claims and no temporal info.

**Example**:
```
Query: "Is the Earth flat or round?"

Source A (Text, reliability=0.5): "Earth is flat"
Source B (Text, reliability=0.5): "Earth is round"

Expected Behavior:
- ✓ Detect DIRECT_CONTRADICTION
- ✓ Equal reliability (0.5 = 0.5)
- ✓ No temporal markers
- ✓ Apply INSUFFICIENT_EVIDENCE resolution
- ✓ Accept: None
- ✓ Confidence: 0.20
```

**Test File**: `test_rag_system.py::TestInsufficientEvidence`

**Related Tests**:
- `test_equal_reliability_no_temporal()` - Validates insufficient evidence handling

---

### Edge Case 8: Determinism & Replay

**Description**: Identical inputs must produce identical outputs (guaranteed).

**Example**:
```
Input:
- Query: "What is the capital of France?"
- Data: "Paris is the capital of France" (PDF)

Run 1: Answer: "Paris...", Confidence: 0.95, Hash: abc123
Run 2: Answer: "Paris...", Confidence: 0.95, Hash: abc123
Run 3: Answer: "Paris...", Confidence: 0.95, Hash: abc123

Expected Behavior:
- ✓ All runs produce identical answers
- ✓ All runs produce identical confidence
- ✓ All runs produce identical deterministic hashes
- ✓ Replay verification passes
```

**Test File**: `test_rag_system.py::TestDeterminismAndReplay`

**Related Tests**:
- `test_replay_produces_same_results()` - Validates replay consistency
- `test_deterministic_hash_matches()` - Validates hash matching

---

### Edge Case 9: Performance Constraints

**Description**: Processing completes within 30 seconds per query and <1GB memory.

**Example**:
```
Input: Multiple sources (3+ PDFs, 1000+ chunks)

Expected Behavior:
- ✓ Processing time < 30 seconds
- ✓ Memory usage < 1GB
- ✓ All conflicts detected and resolved
- ✓ Complete audit trail generated
```

**Test File**: `test_rag_system.py::TestPerformance`

**Related Tests**:
- `test_query_processing_under_30_seconds()` - Validates time constraint

---

### Edge Case 10: Idempotency

**Description**: Repeated processing of same query doesn't change results.

**Example**:
```
Query: "What is the capital of England?" (run 3 times)

Run 1: "London [Geography Source]"
Run 2: "London [Geography Source]"
Run 3: "London [Geography Source]"

Expected Behavior:
- ✓ All results identical
- ✓ No side effects between runs
- ✓ System state unchanged
```

**Test File**: `test_rag_system.py::TestIdempotency`

**Related Tests**:
- `test_multiple_queries_idempotent()` - Validates idempotent behavior

---

### Edge Case 11: Temporal Boundary Conditions

**Description**: Correct handling of temporal boundaries (midnight, year transitions).

**Example**:
```
Query: "What happened around the year boundary?"

Source A: "Event on 2023-12-31 23:59"
Source B: "Event on 2024-01-01 00:01"

Expected Behavior:
- ✓ Correctly parse dates
- ✓ Recognize date boundary crossing
- ✓ Prefer more recent (2024-01-01)
- ✓ Temporal markers extracted correctly
```

**Test File**: `test_rag_system.py::TestTemporalBoundaryConditions`

**Related Tests**:
- `test_midnight_boundary_processing()` - Validates midnight handling
- `test_year_boundary_resolution()` - Validates year boundary handling

---

## Running Tests

### All Tests
```bash
pytest test_rag_system.py -v
```

### Specific Edge Case
```bash
# Run direct contradiction tests
pytest test_rag_system.py::TestDirectContradictions -v

# Run temporal tests
pytest test_rag_system.py::TestTemporalConflicts -v

# Run determinism tests
pytest test_rag_system.py::TestDeterminismAndReplay -v
```

### With Coverage
```bash
pytest test_rag_system.py --cov=. --cov-report=html
```

### Verbose with Long Output
```bash
pytest test_rag_system.py -vv --tb=long
```

## Sample Test Data

### Test Document Fixtures

```python
# PDF Document
{
    "type": "pdf",
    "source_name": "Professional Resume",
    "content": "John Smith is a certified software engineer...",
    "reliability_score": 1.0,
    "chunk_count": 5
}

# YouTube Video
{
    "type": "youtube",
    "source_name": "Interview 2024",
    "url": "https://www.youtube.com/watch?v=...",
    "reliability_score": 0.7,
    "chunk_count": 10
}

# Text Snippet
{
    "type": "text",
    "source_name": "Social Media",
    "content": "John is practicing law...",
    "reliability_score": 0.5,
    "chunk_count": 2
}
```

### Fact Fixtures

```python
# High-reliability fact
Fact(
    text="John is a software engineer",
    source_name="Professional Resume",
    source_type="pdf",
    reliability_score=1.0,
    temporal_markers=[]
)

# Temporal fact
Fact(
    text="John was a doctor in 2020",
    source_name="Biography",
    source_type="youtube",
    reliability_score=0.7,
    temporal_markers=["2020"]
)

# Low-reliability fact
Fact(
    text="John might be a lawyer",
    source_name="Forum Comment",
    source_type="text",
    reliability_score=0.3,
    temporal_markers=[]
)
```

## Test Fixtures Directory

```
fixtures/
├── edge_case_scenarios.json      # All 11 edge case descriptions
├── sample_audit_trace.json       # Example audit trail output
├── sample_pdf_text.txt           # Sample PDF document content
├── sample_youtube_transcript.json # Sample YouTube transcript
└── sample_user_snippets.json     # Sample user text snippets
```

## Expected Test Results

### Coverage
- Total test methods: 45+
- Total assertions: 100+
- Coverage: >90%

### Execution Time
- Full test suite: ~30-60 seconds
- Individual test: 100-500ms

### Pass Rate
- Target: 100%
- All edge cases: Covered
- All integration paths: Covered

## Verifying Edge Cases

Each edge case can be manually tested using the Streamlit UI:

### To Test Direct Contradiction:
1. Open `app.py`
2. Upload/enter two conflicting texts:
   - "John is a doctor"
   - "John is a lawyer"
3. Query: "What is John's profession?"
4. Verify conflict detected and resolved

### To Test Temporal Conflict:
1. Enter two texts with different dates:
   - "In 2020, John was an engineer"
   - "In 2024, John is a manager"
2. Query: "What is John's current role?"
3. Verify 2024 fact is accepted

### To Test Determinism:
1. Process a query
2. Export audit trail (note trace ID and hash)
3. Run replay verification
4. Verify deterministic_hash matches

### To Test Performance:
1. Upload multiple large PDFs
2. Enter complex query
3. Check processing time < 30 seconds
4. Verify memory usage < 1GB

## Integration Tests

The test suite includes integration tests that validate:

✓ End-to-end workflow (ingest → detect → resolve → answer)
✓ Audit trail completeness (all fields populated)
✓ Determinism across multiple runs
✓ Conflict resolution with real documents
✓ Error handling and edge cases

## Fixture Format

### JSON Fixture Structure

```json
{
  "edge_case_scenarios": [
    {
      "id": 1,
      "title": "Edge Case Name",
      "description": "What this edge case tests",
      "scenario": {
        "query": "User query",
        "sources": [
          {
            "type": "pdf|youtube|text",
            "name": "Source name",
            "text": "Content",
            "reliability": 0.5,
            "temporal_marker": "2024"
          }
        ],
        "expected_conflict": "CONFLICT_TYPE",
        "expected_resolution": "Resolution strategy",
        "expected_confidence": 0.85
      }
    }
  ]
}
```

## Common Test Patterns

### Pattern 1: Create and Compare Facts
```python
def test_conflict_scenario(conflict_detector):
    fact1 = create_test_fact("Fact A", "Source 1")
    fact2 = create_test_fact("Fact B", "Source 2")
    
    conflicts = conflict_detector.detect_conflicts([fact1, fact2])
    
    assert len(conflicts) >= 1
    assert conflicts[0].conflict_type == ConflictType.DIRECT_CONTRADICTION
```

### Pattern 2: Resolve Conflict
```python
def test_resolution_logic(conflict_resolver):
    conflict = Conflict(...facts...)
    resolution = conflict_resolver.resolve_conflict(conflict)
    
    assert resolution.accepted_fact is not None
    assert resolution.confidence_score > 0.5
    assert resolution.resolution_strategy == ResolutionStrategy.SOURCE_RELIABILITY
```

### Pattern 3: Verify Determinism
```python
def test_deterministic_output(rag_system):
    result1 = rag_system.process_query(query)
    result2 = rag_system.process_query(query)
    
    assert result1["answer"] == result2["answer"]
    assert result1["confidence"] == result2["confidence"]
```

## Troubleshooting Tests

**Issue**: Test fails due to embedding model download
**Solution**: Models are cached. First run downloads ~80MB. Requires internet.

**Issue**: Test times out
**Solution**: Run tests without YouTube (requires internet). Skip with: `-m "not youtube"`

**Issue**: Assertion fails unexpectedly
**Solution**: Run with verbose output: `pytest -vv --tb=long`

## Next Steps

To add new edge cases:

1. **Define the scenario** in `fixtures/edge_case_scenarios.json`
2. **Create test class** in `test_rag_system.py`
3. **Implement test methods** with fixtures
4. **Verify behavior** matches specification
5. **Document** in this file

Example:

```python
class TestNewEdgeCase:
    """Test description."""
    
    def test_new_scenario(self, rag_system):
        """Test implementation."""
        # Arrange
        rag_system.ingest_text("Test data", "Source")
        
        # Act
        result = rag_system.process_query("Query?")
        
        # Assert
        assert result["expected_field"] == "expected_value"
```

---

**Last Updated**: January 2024

**Status**: All 11 edge cases covered ✓
