"""
Multi-source ingestion pipeline for Temporal Conflict Resolution RAG system.
Handles PDFs, YouTube transcripts, and text snippets.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import re
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


@dataclass
class Document:
    """Represents a document with metadata for conflict resolution."""
    id: str  # Unique document ID
    source_type: str  # "pdf", "youtube", or "text"
    source_name: str  # File name, URL, or snippet identifier
    content: str  # Document content
    chunk_index: int  # Chunk number within document
    chunk_size: int  # Total chunks in document
    embedding: Optional[List[float]] = None  # Vector embedding
    timestamp: str = None  # ISO format timestamp when ingested
    reliability_score: float = 1.0  # Source reliability (0-1)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class SourceIngestionPipeline:
    """Manages multi-source document ingestion with embeddings."""
    
    # Source reliability scores (used in conflict resolution)
    RELIABILITY_SCORES = {
        "pdf": 1.0,
        "youtube": 0.7,
        "text": 0.5
    }
    
    CHUNK_SIZE = 512  # tokens equivalent (using char count as proxy)
    CHUNK_OVERLAP = 50
    
    def __init__(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the ingestion pipeline.
        
        Args:
            embedding_model: HuggingFace model name for embeddings
        """
        self.embedding_model = HuggingFaceEmbeddings(model_name=embedding_model)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""]
        )
        self.documents: List[Document] = []
    
    def ingest_pdf(self, file_path: str, source_name: Optional[str] = None) -> List[Document]:
        """
        Ingest a PDF file and return chunked documents with embeddings.
        
        Args:
            file_path: Path to PDF file
            source_name: Optional human-readable name for the source
            
        Returns:
            List of Document objects
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        source_name = source_name or Path(file_path).name
        loader = PyPDFLoader(file_path)
        raw_docs = loader.load()
        
        # Combine all pages into single text
        full_text = "\n\n".join([doc.page_content for doc in raw_docs])
        
        # Split into chunks
        chunks = self.text_splitter.split_text(full_text)
        
        documents = []
        for idx, chunk in enumerate(chunks):
            doc = self._create_document(
                source_type="pdf",
                source_name=source_name,
                content=chunk,
                chunk_index=idx,
                total_chunks=len(chunks)
            )
            documents.append(doc)
        
        self.documents.extend(documents)
        return documents
    
    def ingest_youtube(self, video_url: str) -> List[Document]:
        """
        Ingest a YouTube video transcript and return chunked documents.
        
        Args:
            video_url: YouTube URL or video ID
            
        Returns:
            List of Document objects
        """
        # Extract video ID from URL
        video_id = self._extract_youtube_id(video_url)
        
        try:
            # Try to fetch transcript with language fallback
            api = YouTubeTranscriptApi()
            
            # First, try to get available transcripts
            try:
                # Try multiple languages: English, Spanish, French, German, Hindi, and any available
                transcript_data = api.fetch(video_id, languages=['en', 'es', 'fr', 'de', 'hi'])
            except NoTranscriptFound:
                # If those don't work, get the list of available transcripts and use the first one
                transcript_list = api.list(video_id)
                # Try to find any available transcript (including auto-generated)
                available_transcripts = transcript_list.get_available_transcripts()
                if available_transcripts.manual_transcripts:
                    transcript = list(available_transcripts.manual_transcripts)[0]
                elif available_transcripts.generated_transcripts:
                    transcript = list(available_transcripts.generated_transcripts)[0]
                else:
                    raise ValueError(f"No transcripts available for video {video_url}")
                transcript_data = transcript.fetch()
            
            full_text = "\n".join([item.text for item in transcript_data])
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            raise ValueError(f"Could not fetch transcript for video {video_url}: {e}")
        
        # Split into chunks
        chunks = self.text_splitter.split_text(full_text)
        
        documents = []
        for idx, chunk in enumerate(chunks):
            doc = self._create_document(
                source_type="youtube",
                source_name=f"YouTube: {video_id}",
                content=chunk,
                chunk_index=idx,
                total_chunks=len(chunks)
            )
            documents.append(doc)
        
        self.documents.extend(documents)
        return documents
    
    def ingest_text(self, text: str, source_name: str = "user_text") -> List[Document]:
        """
        Ingest free-form text snippet and return chunked documents.
        
        Args:
            text: Text content
            source_name: Identifier for the text snippet
            
        Returns:
            List of Document objects
        """
        # Split into chunks
        chunks = self.text_splitter.split_text(text)
        
        documents = []
        for idx, chunk in enumerate(chunks):
            doc = self._create_document(
                source_type="text",
                source_name=source_name,
                content=chunk,
                chunk_index=idx,
                total_chunks=len(chunks)
            )
            documents.append(doc)
        
        self.documents.extend(documents)
        return documents
    
    def _create_document(
        self,
        source_type: str,
        source_name: str,
        content: str,
        chunk_index: int,
        total_chunks: int
    ) -> Document:
        """Create a Document object with embedding and metadata."""
        # Generate unique ID
        doc_id = self._generate_id(source_name, chunk_index)
        
        # Generate embedding
        embedding = self.embedding_model.embed_query(content)
        
        # Create document
        doc = Document(
            id=doc_id,
            source_type=source_type,
            source_name=source_name,
            content=content,
            chunk_index=chunk_index,
            chunk_size=total_chunks,
            embedding=embedding,
            timestamp=datetime.utcnow().isoformat(),
            reliability_score=self.RELIABILITY_SCORES.get(source_type, 0.5)
        )
        
        return doc
    
    def _generate_id(self, source_name: str, chunk_index: int) -> str:
        """Generate a deterministic ID for a document chunk."""
        seed = f"{source_name}_{chunk_index}"
        return hashlib.md5(seed.encode()).hexdigest()[:12]
    
    def _extract_youtube_id(self, url: str) -> str:
        """Extract YouTube video ID from various URL formats."""
        patterns = [
            r"(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)",
            r"^([a-zA-Z0-9_-]{11})$"  # Direct video ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract YouTube video ID from: {url}")
    
    def get_all_documents(self) -> List[Document]:
        """Return all ingested documents."""
        return self.documents
    
    def clear_documents(self):
        """Clear all ingested documents."""
        self.documents = []
