"""
Import handler — processes conversation exports into governed artifacts.

Every import creates:
- Artifact ownership records (entity-bound)
- A provenance chain (source → artifacts)
- An import receipt (governance evidence)

The authority chain is enforced but the importer itself does not
evaluate permissions — it receives the governance outcome from
the caller and records it in the receipt.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid

from src.artifacts.ownership import ArtifactOwnership
from src.provenance.chain import ProvenanceChain


@dataclass
class ImportReceipt:
    """Receipt for a conversation import operation."""
    receipt_id: str
    imported_at: str
    source: dict
    artifacts: list[dict]
    provenance_chain: dict
    governance: dict
    evidence_refs: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "receipt_schema": "ci-import-receipt-v1",
            "receipt_id": self.receipt_id,
            "imported_at": self.imported_at,
            "source": self.source,
            "artifacts": self.artifacts,
            "provenance_chain": self.provenance_chain,
            "governance": self.governance,
            "evidence_refs": self.evidence_refs
        }


class ImportHandler:
    """Handles conversation imports, building the authority chain."""
    
    def __init__(self, owner_entity: str = "default"):
        self.owner_entity = owner_entity
    
    def process_export(self, provider: str, export_id: str,
                       file_hash: Optional[str] = None,
                       governance_outcome: Optional[dict] = None) -> ImportReceipt:
        """
        Process a conversation export import.
        
        This is the core authority chain builder. It:
        1. Creates a provenance chain rooted at the source export
        2. Creates artifact ownership records
        3. Generates an import receipt
        
        No RAG or Obsidian projection is performed at this stage.
        """
        # Default governance outcome if not provided
        if governance_outcome is None:
            governance_outcome = {
                "entity": self.owner_entity,
                "decision_id": f"ci-decision-{uuid.uuid4().hex[:12]}",
                "permission": "entity.self.artifact.register",
                "outcome": "allowed"
            }
        
        # Create provenance chain
        chain = ProvenanceChain(provider, export_id, file_hash)
        
        # Create ownership manager
        ownership = ArtifactOwnership(
            owner_entity=governance_outcome.get("entity", self.owner_entity),
            import_session_id=chain.import_session_id
        )
        
        # Register the conversation artifact (root of all derived artifacts)
        conversation = ownership.register_artifact(
            artifact_type="conversation",
            source_provider=provider,
            source_export_id=export_id,
            provenance_id=chain.chain_id
        )
        
        # Add provenance entry: source_export → conversation
        chain.add_entry(
            from_id="source_export",
            to_id=conversation.artifact_id,
            transformation="import",
            detail=f"Imported {provider} export {export_id}"
        )
        
        # Build receipt
        receipt = ImportReceipt(
            receipt_id=f"ci-receipt-{uuid.uuid4().hex[:12]}",
            imported_at=datetime.now(timezone.utc).isoformat(),
            source={
                "provider": provider,
                "export_id": export_id,
                "exported_at": chain.source_export["exported_at"],
                "file_hash": file_hash or ""
            },
            artifacts=ownership.get_artifacts(),
            provenance_chain=chain.to_dict(),
            governance=governance_outcome,
            evidence_refs=[
                f"provenance:{chain.chain_id}",
                f"ownership:{ownership.import_session_id}"
            ]
        )
        
        return receipt
    
    def generate_mock_receipt(self) -> ImportReceipt:
        """Generate a mock receipt for schema validation."""
        return self.process_export(
            provider="claude",
            export_id="export-mock-001",
            file_hash="a" * 64
        )
