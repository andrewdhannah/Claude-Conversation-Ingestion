"""
Artifact ownership model — Raw artifact ownership without persistence.

Defines the ownership contract for conversation artifacts.
Each artifact is owned by the importing entity and traces
back to its source export via the provenance chain.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class OwnershipRecord:
    """Record of artifact ownership at creation time."""
    artifact_id: str
    artifact_type: str  # conversation, message, project_match, extracted_entity
    owner_entity: str
    import_session_id: str
    source_provider: str
    source_export_id: str
    provenance_id: str
    claimed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    lifecycle_state: str = "active"
    
    def to_dict(self):
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "ownership": {
                "owner_entity": self.owner_entity,
                "import_session_id": self.import_session_id,
                "claimed_at": self.claimed_at
            },
            "source_export": {
                "provider": self.source_provider,
                "export_id": self.source_export_id
            },
            "provenance_id": self.provenance_id,
            "lifecycle_state": self.lifecycle_state
        }


class ArtifactOwnership:
    """Manages artifact ownership records for an import session."""
    
    def __init__(self, owner_entity: str, import_session_id: Optional[str] = None):
        self.owner_entity = owner_entity
        self.import_session_id = import_session_id or f"ci-import-{uuid.uuid4().hex[:12]}"
        self.artifacts: list[OwnershipRecord] = []
    
    def register_artifact(self, artifact_type: str, source_provider: str,
                          source_export_id: str, provenance_id: str) -> OwnershipRecord:
        """Register a new artifact with ownership."""
        artifact_id = f"ci-artifact-{uuid.uuid4().hex[:12]}"
        record = OwnershipRecord(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            owner_entity=self.owner_entity,
            import_session_id=self.import_session_id,
            source_provider=source_provider,
            source_export_id=source_export_id,
            provenance_id=provenance_id
        )
        self.artifacts.append(record)
        return record
    
    def get_artifacts(self) -> list[dict]:
        """Return all registered artifacts as dicts."""
        return [a.to_dict() for a in self.artifacts]
    
    def get_summary(self) -> dict:
        """Return ownership summary for receipt generation."""
        return {
            "import_session_id": self.import_session_id,
            "owner_entity": self.owner_entity,
            "total_artifacts": len(self.artifacts),
            "artifact_types": dict(
                (t, sum(1 for a in self.artifacts if a.artifact_type == t))
                for t in set(a.artifact_type for a in self.artifacts)
            )
        }
