"""
Provenance chain — tracks artifact transformations from source to derived form.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class ProvenanceEntry:
    """A single step in the provenance chain."""
    entry_id: str
    from_id: str  # source artifact ID or 'source_export'
    to_id: str    # target artifact ID
    transformation: str  # import, extract, derive, link, export
    transformation_detail: str = ""
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence_ref: Optional[str] = None
    
    def to_dict(self):
        return {
            "entry_id": self.entry_id,
            "from": self.from_id,
            "to": self.to_id,
            "transformation": self.transformation,
            "transformation_detail": self.transformation_detail,
            "recorded_at": self.recorded_at,
            "evidence_ref": self.evidence_ref
        }


class ProvenanceChain:
    """A provenance chain for a single import session."""
    
    def __init__(self, provider: str, export_id: str, file_hash: Optional[str] = None):
        self.chain_id = f"ci-provenance-{uuid.uuid4().hex[:12]}"
        self.import_session_id = f"ci-import-{uuid.uuid4().hex[:12]}"
        self.source_export = {
            "provider": provider,
            "export_id": export_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "file_hash": file_hash or ""
        }
        self.entries: list[ProvenanceEntry] = []
    
    def add_entry(self, from_id: str, to_id: str, transformation: str,
                  detail: str = "", evidence_ref: Optional[str] = None) -> ProvenanceEntry:
        """Add a provenance chain entry."""
        entry = ProvenanceEntry(
            entry_id=f"ci-prov-{uuid.uuid4().hex[:12]}",
            from_id=from_id,
            to_id=to_id,
            transformation=transformation,
            transformation_detail=detail,
            evidence_ref=evidence_ref
        )
        self.entries.append(entry)
        return entry
    
    def get_terminal_artifacts(self) -> list[str]:
        """Return artifacts that are not sources for any other entry."""
        sources = {e.from_id for e in self.entries}
        targets = {e.to_id for e in self.entries}
        return list(targets - sources)
    
    def to_dict(self) -> dict:
        """Serialize the full provenance chain."""
        return {
            "provenance_schema": "ci-provenance-chain-v1",
            "chain_id": self.chain_id,
            "import_session_id": self.import_session_id,
            "source_export": self.source_export,
            "entries": [e.to_dict() for e in self.entries],
            "terminal_artifacts": self.get_terminal_artifacts()
        }
