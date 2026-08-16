# 🎯 Temporal Conflict Resolution RAG System

[![GitHub](https://img.shields.io/badge/GitHub-Khushwant123--x/Assessment-blue?logo=github)](https://github.com/Khushwant123-x/Assessment)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)

> **Transform conflicting information into reliable, structured answers with full auditability and transparency.**

A production-ready **Retrieval-Augmented Generation (RAG)** system that detects and resolves information conflicts across multiple sources using temporal ordering, source reliability hierarchies, and deterministic resolution strategies.

---

## 🚀 Key Features

### 🔍 Multi-Source Ingestion
- **PDF Processing** - Extract and embed text from PDF documents
- **YouTube Transcripts** - Fetch and process video transcripts (with language fallback)
- **Text Snippets** - Ingest user-provided text with automatic chunking
- **Auto-embedding** - Generate semantic embeddings using sentence-transformers

### ⚡ Intelligent Conflict Detection
- **Direct Contradictions** - Identify opposite claims (e.g., "alive" vs "dead")
- **Temporal Conflicts** - Detect time-based inconsistencies
- **Severity Classification** - High/Medium/Low conflict levels
- **Source Analysis** - Track which sources contribute to conflicts

### ✅ Deterministic Resolution
- **Source Reliability Hierarchy** - PDF (1.0) > YouTube (0.7) > Text (0.5)
- **Temporal Recency** - Prioritize recent information
- **Internal Consistency** - Resolve circular dependencies
- **Insufficient Evidence Handling** - Transparent handling of unresolvable conflicts

### 📊 Structured Output (ChatGPT/Claude-style)
- **Summary Section** - Main answer at top
- **Key Points** - Organized bullet points
- **Details by Source** - Facts grouped hierarchically
- **Confidence Indicators** - ✓ High / ◆ Medium / ○ Lower
- **Metrics Dashboard** - Confidence scores, source count, facts verified

### 🔐 Complete Auditability
- **JSON Audit Trails** - Every decision captured
- **Deterministic Hashing** - Verify replay consistency
- **Decision Explanation** - Why each fact was accepted/rejected
- **Query History** - Track all previous queries

### 🧪 Comprehensive Testing
- **45+ Test Cases** - Covering 11+ edge cases
- **Edge Case Fixtures** - Pre-built test scenarios
- **Integration Tests** - End-to-end workflow validation
- **Performance Tests** - <30s per query, <1GB memory

---

## 📋 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Khushwant123-x/Assessment.git
cd Assessment

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run the Streamlit App

```bash
streamlit run app.py
```

Access at: `http://localhost:8501`

### Python API Usage

```python
from rag_orchestrator import TemporalConflictRAG

# Initialize system
rag = TemporalConflictRAG()

# Ingest sources
rag.ingest_pdf("document.pdf", source_name="Company Report")
rag.ingest_youtube("https://youtu.be/dQw4w9WgXcQ")
rag.ingest_text("Apple was founded in 1976", source_name="User Input")

# Process query
result = rag.process_query("When was Apple founded?")

print(result["answer"])
print(f"Confidence: {result['confidence']:.1%}")
print(f"Conflicts Detected: {result['conflicts_detected']}")
```

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────┐
│      Streamlit Web UI (app.py)      │
│  Multi-source Ingestion & Querying  │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│    RAG Orchestrator                 │
│ - Coordinates all components        │
│ - Manages workflow                  │
│ - Generates final answer            │
└──┬──────┬──────────┬────────────┬───┘
   │      │          │            │
   ▼      ▼          ▼            ▼
┌──────┬──────┬───────────┬────────────┐
│ PDF  │  YT  │ Text      │ Embedding  │
│ Load │ Tx   │ Ingest    │ Model      │
└──────┴──────┴───────────┴────────────┘
        Ingestion Pipeline
        
        │
        ▼
┌─────────────────────────────────────┐
│  Conflict Detection Engine          │
│  - Extract facts                    │
│  - Identify contradictions          │
│  - Calculate severity               │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  Conflict Resolution Engine         │
│  - Apply resolution rules           │
│  - Generate explanations            │
│  - Calculate confidence             │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  Audit Trace Generator              │
│  - Log all decisions                │
│  - Generate deterministic hash      │
│  - Enable replay verification       │
└─────────────────────────────────────┘
```

### Core Modules

| Module | Purpose | Key Classes |
|--------|---------|------------|
| **ingestion_pipeline.py** | Multi-source document ingestion | `SourceIngestionPipeline`, `Document` |
| **conflict_detection.py** | Fact extraction & conflict identification | `ConflictDetector`, `Fact`, `Conflict` |
| **conflict_resolution.py** | Deterministic conflict resolution | `ConflictResolver`, `Resolution` |
| **audit_trace.py** | Complete decision tracking | `AuditTraceGenerator`, `DecisionTrace` |
| **rag_orchestrator.py** | Workflow orchestration | `TemporalConflictRAG` |
| **app.py** | Streamlit user interface | Multi-page web application |

---

## 🔄 How It Works

### 1. Document Ingestion
```
PDF/YouTube/Text → Text Extraction → Chunking → Embedding → Storage
```

### 2. Query Processing
```
User Query → Document Retrieval → Fact Extraction → Conflict Detection
    ↓
Conflict Resolution → Answer Generation → Audit Trail Creation
```

### 3. Conflict Resolution Process
```
Conflicting Facts:
  - Fact A: "Event happened in 2020" (PDF, reliability: 1.0)
  - Fact B: "Event happened in 2019" (YouTube, reliability: 0.7)

Resolution Strategy: SOURCE_RELIABILITY
  → PDF has higher reliability (1.0 > 0.7)
  → Accept Fact A (2020)
  → Reject Fact B
  → Confidence: 0.95 (high reliability source)
```

---

## 📊 Output Example

### Structured Answer Format

```
Summary
The Apple I was released on April 16, 1976 at the Homebrew Computer Club.

Key Points
• Apple I was designed by Steve Wozniak
• It was released at the Homebrew Computer Club meeting
• Price was $666.66

Details by Source
**Wikipedia (PDF)**
• The Apple I was Apple Computer's first product
  ✓ High confidence
• It was released on April 16, 1976
  ✓ High confidence

**YouTube Tutorial**
• Steve Wozniak personally demonstrated the Apple I
  ◆ Medium confidence

Confidence Metrics
• Overall Confidence: 92.5%
• Sources Analyzed: 2
• Facts Verified: 4
• Conflicting Claims Resolved: 1
```

---

## 🧪 Testing

### Run All Tests
```bash
pytest test_rag_system.py -v
```

### Run Specific Test Class
```bash
pytest test_rag_system.py::DirectContradictions -v
```

### Run with Coverage
```bash
pytest test_rag_system.py --cov=. --cov-report=html
```

### Test Coverage
- ✅ 45+ test cases
- ✅ 11+ edge case scenarios
- ✅ Integration tests
- ✅ Performance benchmarks
- ✅ Determinism verification

---

## 🎯 Edge Cases Handled

1. **Direct Contradictions** - Same subject, opposite facts
2. **Temporal Conflicts** - Time-based inconsistencies
3. **Source Reliability Hierarchy** - Prioritization rules
4. **Duplicate Events** - Identical facts don't create conflicts
5. **Late Arriving Data** - New information after initial processing
6. **Internal Inconsistency** - Circular dependencies within one source
7. **Insufficient Evidence** - Equal reliability, no temporal markers
8. **Determinism & Replay** - Identical inputs → identical outputs
9. **Performance** - <30 seconds per query, <1GB memory
10. **Idempotency** - Multiple queries produce identical results
11. **Temporal Boundaries** - Midnight/year transitions

---

## 📁 Project Structure

```
Assessment/
├── app.py                          # Streamlit web application
├── rag_orchestrator.py             # Main orchestrator
├── ingestion_pipeline.py           # Multi-source ingestion
├── conflict_detection.py           # Conflict detection engine
├── conflict_resolution.py          # Resolution strategies
├── audit_trace.py                  # Audit trail generation
├── test_rag_system.py              # 45+ comprehensive tests
├── requirements.txt                # Dependencies
├── README.md                       # Documentation
├── FIXTURES.md                     # Edge case documentation
├── .gitignore                      # Git ignore rules
├── .gitattributes                  # Line ending configuration
├── LICENSE                         # MIT License
└── fixtures/
    ├── edge_case_scenarios.json    # Test fixture definitions
    └── sample_audit_trace.json     # Example audit trail
```

---

## 🔧 Configuration

### Environment Variables (Optional)

Create a `.env` file:
```env
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LOG_LEVEL=INFO
CACHE_DIR=.cache
```

### Dependencies

See `requirements.txt` for complete list:
- langchain (0.1.0+) - RAG orchestration
- sentence-transformers (2.2.0+) - Semantic embeddings
- youtube-transcript-api (0.6.1+) - YouTube integration
- streamlit (1.28.0+) - Web UI
- pypdf (3.17.0+) - PDF processing
- pytest (7.4.0+) - Testing framework

---

## 📈 Performance

| Metric | Value | Notes |
|--------|-------|-------|
| Query Processing Time | <30 seconds | Typical: 5-15s |
| Memory Usage | <1GB | Per query |
| Embedding Generation | 5-10s | First run includes model download |
| PDF Processing | ~1s per MB | Depends on PDF complexity |
| Test Execution | ~45s | Full test suite |

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 🎓 How to Use This System

### For Researchers
- Explore conflict resolution strategies in multi-source scenarios
- Study deterministic decision-making in information systems
- Analyze temporal reasoning algorithms

### For Developers
- Integrate as a dependency in larger RAG systems
- Build upon the conflict detection framework
- Extend with custom resolution strategies

### For Organizations
- Validate information across multiple sources
- Create audit trails for compliance requirements
- Build trustworthy AI-powered Q&A systems

---

## 📞 Support & Issues

Found a bug? Have a feature request? Please [open an issue](https://github.com/Khushwant123-x/Assessment/issues) on GitHub!

---

## 🎉 Get Started

```bash
# Clone and setup
git clone https://github.com/Khushwant123-x/Assessment.git
cd Assessment
pip install -r requirements.txt

# Run the app
streamlit run app.py

# Or run tests
pytest test_rag_system.py -v
```

**Happy coding!** 🚀
