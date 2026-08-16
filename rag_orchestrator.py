"""
Main RAG orchestrator for temporal conflict resolution.
Coordinates ingestion, conflict detection, resolution, and audit trails.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import time

from ingestion_pipeline import SourceIngestionPipeline, Document
from conflict_detection import ConflictDetector, Fact, Conflict
from conflict_resolution import ConflictResolver, Resolution
from audit_trace import AuditTraceGenerator, DecisionTrace


class TemporalConflictRAG:
    """Main orchestrator for the temporal conflict resolution RAG system."""
    
    def __init__(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the RAG system.
        
        Args:
            embedding_model: HuggingFace model for embeddings
        """
        self.ingestion_pipeline = SourceIngestionPipeline(embedding_model)
        self.conflict_detector = ConflictDetector()
        self.conflict_resolver = ConflictResolver()
        self.audit_generator = AuditTraceGenerator()
        
        self.all_documents: List[Document] = []
        self.all_facts: List[Fact] = []
        self.all_conflicts: List[Conflict] = []
        self.all_resolutions: List[Resolution] = []
    
    def ingest_pdf(self, file_path: str, source_name: Optional[str] = None) -> List[Document]:
        """Ingest a PDF file."""
        docs = self.ingestion_pipeline.ingest_pdf(file_path, source_name)
        self.all_documents.extend(docs)
        return docs
    
    def ingest_youtube(self, video_url: str) -> List[Document]:
        """Ingest a YouTube video transcript."""
        docs = self.ingestion_pipeline.ingest_youtube(video_url)
        self.all_documents.extend(docs)
        return docs
    
    def ingest_text(self, text: str, source_name: str = "user_text") -> List[Document]:
        """Ingest a text snippet."""
        docs = self.ingestion_pipeline.ingest_text(text, source_name)
        self.all_documents.extend(docs)
        return docs
    
    def process_query(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """
        Process a user query end-to-end.
        
        Steps:
        1. Retrieve relevant documents
        2. Extract facts
        3. Detect conflicts
        4. Resolve conflicts
        5. Generate answer
        6. Create audit trail
        
        Args:
            query: User query
            top_k: Number of top documents to retrieve
            
        Returns:
            Dictionary with answer, confidence, conflicts, and audit trace
        """
        start_time = time.time()
        
        # Create audit trace
        trace_id = self.audit_generator.create_trace(query)
        
        # Step 1: Retrieve relevant documents
        retrieved_docs = self._retrieve_relevant_documents(query, top_k)
        self.audit_generator.record_sources_considered(trace_id, retrieved_docs)
        
        # Step 2: Extract facts
        facts = self.conflict_detector.extract_facts_from_documents(retrieved_docs)
        self.all_facts.extend(facts)
        self.audit_generator.record_facts_extracted(trace_id, facts)
        
        # Step 3: Detect conflicts
        conflicts = self.conflict_detector.detect_conflicts(facts)
        self.all_conflicts.extend(conflicts)
        self.audit_generator.record_conflicts_detected(trace_id, conflicts)
        
        # Step 4: Resolve conflicts
        resolutions = self.conflict_resolver.resolve_all_conflicts(conflicts)
        self.all_resolutions.extend(resolutions)
        self.audit_generator.record_conflicts_resolved(trace_id, resolutions)
        
        # Step 5: Generate answer
        final_answer, accepted_facts, rejected_facts, confidence = self._generate_answer(
            query, facts, resolutions
        )
        
        # Step 6: Record final decision
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        self.audit_generator.record_final_decision(
            trace_id,
            final_answer,
            accepted_facts,
            rejected_facts,
            confidence,
            processing_time
        )
        
        return {
            "query": query,
            "answer": final_answer,
            "confidence": confidence,
            "sources_count": len(set(d.source_name for d in retrieved_docs)),
            "facts_extracted": len(facts),
            "conflicts_detected": len(conflicts),
            "conflicts_resolved": len(resolutions),
            "high_severity_conflicts": len([c for c in conflicts if c.severity == "high"]),
            "audit_trace": self.audit_generator.get_trace(trace_id),
            "trace_id": trace_id
        }
    
    def _retrieve_relevant_documents(self, query: str, top_k: int) -> List[Document]:
        """
        Retrieve top-k documents most relevant to the query.
        
        Uses simple similarity matching based on embeddings.
        """
        if not self.all_documents:
            return []
        
        # Generate query embedding
        query_embedding = self.ingestion_pipeline.embedding_model.embed_query(query)
        
        # Calculate similarity scores
        similarities = []
        for doc in self.all_documents:
            if doc.embedding:
                similarity = self._cosine_similarity(query_embedding, doc.embedding)
                similarities.append((doc, similarity))
        
        # Sort by similarity and return top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in similarities[:top_k]]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _generate_answer(
        self,
        query: str,
        facts: List[Fact],
        resolutions: List[Resolution]
    ) -> Tuple[str, List[Fact], List[Fact], float]:
        """
        Generate a final answer based on accepted facts.
        
        Returns:
            (answer, accepted_facts, rejected_facts, confidence)
        """
        # Get accepted facts from resolutions
        accepted_facts = []
        rejected_facts = []
        confidence_scores = []
        
        for resolution in resolutions:
            if resolution.accepted_fact:
                accepted_facts.append(resolution.accepted_fact)
                confidence_scores.append(resolution.confidence_score)
            rejected_facts.extend(resolution.rejected_facts)
        
        # Include facts that had no conflicts
        fact_ids_in_resolutions = set()
        for resolution in resolutions:
            for fact in resolution.facts_involved:
                fact_ids_in_resolutions.add(fact.fact_id)
        
        for fact in facts:
            if fact.fact_id not in fact_ids_in_resolutions:
                accepted_facts.append(fact)
                confidence_scores.append(fact.reliability_score)
        
        # Generate answer text
        if not accepted_facts:
            answer = "I could not find reliable information to answer your question. There were conflicting claims from multiple sources that could not be resolved."
            confidence = 0.0
        else:
            # Combine facts into coherent answer
            answer_parts = []
            for fact in sorted(accepted_facts, key=lambda f: f.source_name):
                source_indicator = f"[{fact.source_name}]"
                answer_parts.append(f"{fact.text.strip()} {source_indicator}")
            
            answer = " ".join(answer_parts)
            
            # Calculate overall confidence
            if confidence_scores:
                confidence = sum(confidence_scores) / len(confidence_scores)
            else:
                confidence = 0.5
        
        return answer, accepted_facts, rejected_facts, confidence
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            "total_documents_ingested": len(self.all_documents),
            "total_facts_extracted": len(self.all_facts),
            "total_conflicts_detected": len(self.all_conflicts),
            "high_severity_conflicts": len([c for c in self.all_conflicts if c.severity == "high"]),
            "total_conflicts_resolved": len(self.all_resolutions),
            "resolution_strategies_used": self.conflict_resolver.get_resolution_statistics(),
            "sources_by_type": self._count_sources_by_type()
        }
    
    def _count_sources_by_type(self) -> Dict[str, int]:
        """Count ingested documents by source type."""
        counts = {}
        for doc in self.all_documents:
            counts[doc.source_type] = counts.get(doc.source_type, 0) + 1
        return counts
    
    def export_audit_trails(self, output_dir: str = "audit_trails"):
        """Export all audit trails to JSON files."""
        self.audit_generator.export_audit_trail(output_dir)
    
    def save_audit_trace(self, trace_id: str, file_path: str):
        """Save a specific audit trace to file."""
        self.audit_generator.save_trace(trace_id, file_path)
    
    def replay_query(self, trace_id: str) -> Dict[str, Any]:
        """
        Replay a previous query to verify determinism.
        
        Args:
            trace_id: ID of the trace to replay
            
        Returns:
            Comparison of original and replayed results
        """
        original_trace = self.audit_generator.get_trace(trace_id)
        
        if not original_trace:
            return {"error": f"Trace {trace_id} not found"}
        
        # Replay the query
        result = self.process_query(original_trace.query)
        new_trace = result["audit_trace"]
        
        # Verify determinism
        is_deterministic = self.audit_generator.verify_replay_determinism(trace_id, new_trace)
        
        return {
            "original_trace_id": trace_id,
            "replayed_trace_id": new_trace.trace_id,
            "is_deterministic": is_deterministic,
            "original_answer": original_trace.final_answer,
            "replayed_answer": new_trace.final_answer,
            "answers_match": original_trace.final_answer == new_trace.final_answer,
            "original_confidence": original_trace.overall_confidence,
            "replayed_confidence": new_trace.overall_confidence
        }
    
    def clear_all(self):
        """Clear all data and reset the system."""
        self.all_documents = []
        self.all_facts = []
        self.all_conflicts = []
        self.all_resolutions = []
        self.ingestion_pipeline.clear_documents()
        self.conflict_detector.clear_conflicts()
        self.conflict_resolver.clear_resolutions()
        self.audit_generator.clear_traces()
