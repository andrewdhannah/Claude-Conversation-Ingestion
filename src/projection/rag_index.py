"""
RAG index projection stub.

A RAG index is a searchable projection of governed artifacts.
It enables retrieval-augmented generation without exposing raw artifacts.

Design rules:
  - The RAG index is a projection, not a data store
  - Deleting the index does not delete source artifacts
  - The index maps artifact_id → searchable chunks
  - Chunks are derived from message content
  - Permission filtering is applied at query time (not index time)

Current state: schema and structure defined, index storage pending
a persistent artifact store implementation.
"""

from datetime import datetime, timezone
from typing import Optional
import json
import uuid


class RAGChunk:
    """A single searchable chunk in the RAG index."""
    
    def __init__(self, chunk_id: str, artifact_id: str,
                 content: str, chunk_type: str,
                 provenance: Optional[dict] = None):
        self.chunk_id = chunk_id
        self.artifact_id = artifact_id
        self.content = content
        self.chunk_type = chunk_type  # "conversation_summary", "message", "extracted_entity"
        self.provenance = provenance or {}
        self.indexed_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "artifact_id": self.artifact_id,
            "content_preview": self.content[:200],
            "content_length": len(self.content),
            "chunk_type": self.chunk_type,
            "provenance": self.provenance,
            "indexed_at": self.indexed_at
        }


class RAGIndexProjection:
    """A RAG index projected from governed conversation artifacts."""
    
    def __init__(self):
        self.index_id = f"ci-rag-{uuid.uuid4().hex[:12]}"
        self.chunks: list[RAGChunk] = []
        self.generated_at = None
    
    def to_dict(self) -> dict:
        return {
            "index_schema": "ci-rag-index-v1",
            "index_id": self.index_id,
            "generated_at": self.generated_at,
            "chunk_count": len(self.chunks),
            "chunks": [c.to_dict() for c in self.chunks[:20]]  # Preview only
        }


class RAGIndexGenerator:
    """Generates a RAG index from governed conversation artifacts.
    
    Stub implementation — chunks are generated in-memory.
    A full implementation would persist chunks to a vector database
    or search index with permission-aware query filtering.
    """
    
    def generate_from_receipts(self, receipts: list) -> RAGIndexProjection:
        """Generate a RAG index from import receipts.
        
        Each message becomes a chunk. Conversation summaries are
        derived from message content.
        """
        index = RAGIndexProjection()
        
        for receipt in receipts:
            artifacts = receipt.get("artifacts", [])
            source = receipt.get("source", {})
            
            for artifact in artifacts:
                aid = artifact.get("artifact_id", "")
                atype = artifact.get("artifact_type", "")
                
                # Create provenance link
                prov = {
                    "receipt_id": receipt.get("receipt_id", ""),
                    "provider": source.get("provider", ""),
                    "provenance_chain": receipt.get("provenance_chain", {}).get("chain_id", "")
                }
                
                chunk = RAGChunk(
                    chunk_id=f"ci-chunk-{uuid.uuid4().hex[:12]}",
                    artifact_id=aid,
                    content=f"[{atype}] Artifact: {aid}",
                    chunk_type=atype if atype in ("conversation", "message", "extracted_entity") else "extracted_entity",
                    provenance=prov
                )
                index.chunks.append(chunk)
        
        index.generated_at = datetime.now(timezone.utc).isoformat()
        return index
    
    @staticmethod
    def clear_index(index: RAGIndexProjection):
        """Clear the RAG index without affecting source artifacts."""
        count = len(index.chunks)
        index.chunks.clear()
        return f"Index cleared: {count} chunks removed. Source artifacts unaffected."
