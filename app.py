"""
Streamlit UI for Temporal Conflict Resolution RAG system.
"""

import streamlit as st
from pathlib import Path
import json
import tempfile
import os

from rag_orchestrator import TemporalConflictRAG


# Initialize session state
if "rag_system" not in st.session_state:
    st.session_state.rag_system = TemporalConflictRAG()

if "query_history" not in st.session_state:
    st.session_state.query_history = []


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Temporal Conflict Resolution RAG",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 Temporal Conflict Resolution in Multi-Source RAG")
    st.markdown(
        "An AI assistant that processes PDFs, YouTube transcripts, and text to resolve conflicting information."
    )
    
    # Sidebar for document ingestion
    with st.sidebar:
        st.header("📄 Document Ingestion")
        
        # PDF Upload
        st.subheader("1. Upload PDF")
        pdf_file = st.file_uploader(
            "Choose a PDF file",
            type="pdf",
            key="pdf_uploader"
        )
        
        if pdf_file is not None:
            if st.button("Process PDF"):
                with st.spinner("Processing PDF..."):
                    # Save temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(pdf_file.getbuffer())
                        tmp_path = tmp.name
                    
                    try:
                        docs = st.session_state.rag_system.ingest_pdf(
                            tmp_path,
                            pdf_file.name
                        )
                        st.success(f"✅ Processed {len(docs)} chunks from PDF")
                    except Exception as e:
                        st.error(f"❌ Error processing PDF: {e}")
                    finally:
                        os.unlink(tmp_path)
        
        # YouTube URL
        st.subheader("2. Add YouTube Video")
        youtube_url = st.text_input(
            "Enter YouTube URL",
            placeholder="https://www.youtube.com/watch?v=..."
        )
        
        if youtube_url and st.button("Process YouTube"):
            with st.spinner("Fetching YouTube transcript..."):
                try:
                    docs = st.session_state.rag_system.ingest_youtube(youtube_url)
                    st.success(f"✅ Processed {len(docs)} chunks from YouTube")
                except Exception as e:
                    st.error(f"❌ Error processing YouTube: {e}")
        
        # Text Snippet
        st.subheader("3. Add Text Snippet")
        text_snippet = st.text_area(
            "Enter text content",
            placeholder="Paste or type text here...",
            height=100
        )
        snippet_name = st.text_input(
            "Source name for snippet",
            value="user_text"
        )
        
        if text_snippet and st.button("Process Text"):
            with st.spinner("Processing text..."):
                try:
                    docs = st.session_state.rag_system.ingest_text(
                        text_snippet,
                        snippet_name
                    )
                    st.success(f"✅ Processed {len(docs)} chunks from text")
                except Exception as e:
                    st.error(f"❌ Error processing text: {e}")
        
        # System Statistics
        st.divider()
        st.subheader("📊 System Statistics")
        stats = st.session_state.rag_system.get_statistics()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Documents", stats["total_documents_ingested"])
            st.metric("Total Facts", stats["total_facts_extracted"])
        with col2:
            st.metric("Conflicts Detected", stats["total_conflicts_detected"])
            st.metric("High Severity", stats["high_severity_conflicts"])
    
    # Main content area
    st.header("❓ Query Processing")
    
    query = st.text_input(
        "Enter your question:",
        placeholder="What do you want to know about the documents?"
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        search_button = st.button("🔍 Search & Resolve", use_container_width=True)
    with col2:
        clear_button = st.button("🗑️ Clear All Data", use_container_width=True)
    with col3:
        export_button = st.button("📥 Export Audit Trails", use_container_width=True)
    
    # Handle Clear All
    if clear_button:
        st.session_state.rag_system.clear_all()
        st.session_state.query_history = []
        st.success("✅ System cleared")
        st.rerun()
    
    # Handle Export
    if export_button:
        with st.spinner("Exporting audit trails..."):
            st.session_state.rag_system.export_audit_trails("audit_trails")
            st.success("✅ Audit trails exported to 'audit_trails' directory")
    
    # Process Query
    if search_button and query:
        if st.session_state.rag_system.get_statistics()["total_documents_ingested"] == 0:
            st.warning("⚠️ Please ingest at least one document first!")
        else:
            with st.spinner("Processing query..."):
                result = st.session_state.rag_system.process_query(query)
                st.session_state.query_history.append(result)
                
                # Display Results
                st.divider()
                st.header("📋 Results")
                
                # Answer
                st.subheader("Answer")
                st.info(result["answer"])
                
                # Confidence
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        "Overall Confidence",
                        f"{result['confidence']:.2%}"
                    )
                with col2:
                    st.metric("Sources Used", result["sources_count"])
                with col3:
                    st.metric("Facts Extracted", result["facts_extracted"])
                with col4:
                    st.metric("Conflicts Detected", result["conflicts_detected"])
                
                # Tabs for detailed information
                tab1, tab2, tab3, tab4 = st.tabs(
                    ["Conflicts", "Resolutions", "Audit Trail", "Query History"]
                )
                
                with tab1:
                    st.subheader("Detected Conflicts")
                    trace = result["audit_trace"]
                    
                    if trace.conflicts_detected:
                        for conflict in trace.conflicts_detected:
                            with st.expander(
                                f"⚠️ {conflict['conflict_type'].upper()} - {conflict['severity'].upper()}",
                                expanded=conflict['severity'] == 'high'
                            ):
                                st.write(f"**Description:** {conflict['description']}")
                                st.write(f"**Needs Resolution:** {conflict['resolution_needed']}")
                                
                                st.write("**Facts Involved:**")
                                for fact in conflict['facts_involved']:
                                    st.write(f"- *{fact['source_name']}*: {fact['text'][:100]}...")
                    else:
                        st.success("✅ No conflicts detected")
                
                with tab2:
                    st.subheader("Conflict Resolutions")
                    trace = result["audit_trace"]
                    
                    if trace.conflicts_resolved:
                        for resolution in trace.conflicts_resolved:
                            with st.expander(
                                f"✓ {resolution['resolution_strategy'].upper()}",
                                expanded=True
                            ):
                                st.write(f"**Explanation:** {resolution['explanation']}")
                                st.write(f"**Confidence:** {resolution['confidence_score']:.2%}")
                                
                                if resolution['accepted_fact']:
                                    st.success(
                                        f"**Accepted:** {resolution['accepted_fact']['text'][:80]}... "
                                        f"({resolution['accepted_fact']['source_name']})"
                                    )
                                
                                if resolution['rejected_facts']:
                                    st.warning("**Rejected:**")
                                    for fact in resolution['rejected_facts']:
                                        st.write(f"- {fact['text'][:80]}... ({fact['source_name']})")
                    else:
                        st.info("No conflicts to resolve")
                
                with tab3:
                    st.subheader("Full Audit Trail (JSON)")
                    
                    # Download button for JSON
                    audit_json = trace.to_json()
                    st.download_button(
                        label="Download Full Audit Trail",
                        data=audit_json,
                        file_name=f"audit_{result['trace_id']}.json",
                        mime="application/json"
                    )
                    
                    # Display JSON in expandable section
                    with st.expander("View JSON Details"):
                        st.json(json.loads(audit_json))
                    
                    # Show stats
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Processing Summary**")
                        st.write(f"- Processing Time: {trace.processing_time_ms:.2f}ms")
                        st.write(f"- Query: {trace.query}")
                        st.write(f"- Timestamp: {trace.query_timestamp}")
                    
                    with col2:
                        st.write("**Decision Summary**")
                        st.write(f"- Accepted Facts: {len(trace.accepted_facts)}")
                        st.write(f"- Rejected Facts: {len(trace.rejected_facts)}")
                        st.write(f"- Overall Confidence: {trace.overall_confidence:.2%}")
                
                with tab4:
                    st.subheader("Query History")
                    
                    if st.session_state.query_history:
                        for i, hist_result in enumerate(st.session_state.query_history, 1):
                            with st.expander(
                                f"Query {i}: {hist_result['query'][:50]}...",
                                expanded=(i == len(st.session_state.query_history))
                            ):
                                st.write(f"**Answer:** {hist_result['answer']}")
                                st.write(f"**Confidence:** {hist_result['confidence']:.2%}")
                                st.write(f"**Conflicts Detected:** {hist_result['conflicts_detected']}")
                                st.write(f"**Conflicts Resolved:** {hist_result['conflicts_resolved']}")
                    else:
                        st.info("No queries processed yet")


if __name__ == "__main__":
    main()
