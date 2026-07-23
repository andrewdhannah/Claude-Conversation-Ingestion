"""
Artifact ownership model for conversation ingestion.

Every artifact produced from a conversation import has:
- A unique artifact_id
- An owner entity (who imported it)
- A source export reference
- A provenance chain link
- A lifecycle state

Ownership invariants:
1. Every artifact has exactly one owner at creation
2. Every artifact traces back to its source export
3. Every artifact has a provenance chain entry
4. Artifact lifecycle is governable (active → stale → archived → deleted)
"""

from .ownership import ArtifactOwnership, OwnershipRecord
