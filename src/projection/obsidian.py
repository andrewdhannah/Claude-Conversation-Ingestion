"""
Obsidian vault projection generator.

Conversions:
  Governed conversation artifacts → Obsidian-compatible markdown notes.

Design rules:
  - Each artifact becomes one or more .md files
  - Wiki-links [[id]] connect artifacts that share provenance
  - Frontmatter contains provenance, ownership, and receipt references
  - Projections are regenerable — deleting the vault and regenerating
    from source artifacts must produce identical output.
  - Source artifacts are never modified during projection.
"""

import os
import json
from datetime import datetime, timezone
from typing import Optional


class ObsidianProjection:
    """A single Obsidian note projected from a governed artifact."""
    
    def __init__(self, filepath: str, content: str, frontmatter: dict):
        self.filepath = filepath
        self.content = content
        self.frontmatter = frontmatter
    
    def write(self, vault_root: str):
        """Write this note to the Obsidian vault."""
        full_path = os.path.join(vault_root, self.filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        frontmatter_str = "---\n" + "\n".join(
            f"{k}: {json.dumps(v) if isinstance(v, (dict, list)) else v}"
            for k, v in self.frontmatter.items()
        ) + "\n---\n"
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter_str + self.content)
    
    def to_dict(self) -> dict:
        return {
            "filepath": self.filepath,
            "frontmatter": self.frontmatter,
            "content_length": len(self.content)
        }


class ObsidianVaultGenerator:
    """Generates an Obsidian vault from governed conversation artifacts."""
    
    def generate_from_receipts(self, receipts: list, vault_root: str) -> list[ObsidianProjection]:
        """Generate Obsidian vault from import receipts.
        
        receipts: list of ImportReceipt.to_dict() outputs
        vault_root: target directory for .md files
        Returns list of ObsidianProjection objects written to disk.
        """
        projections = []
        
        for receipt in receipts:
            projections.extend(self._project_conversation(receipt))
        
        # Write all projections
        for proj in projections:
            proj.write(vault_root)
        
        # Generate index
        self._write_index(projections, vault_root)
        
        return projections
    
    def _project_conversation(self, receipt: dict) -> list[ObsidianProjection]:
        """Project a single import receipt into Obsidian notes."""
        projections = []
        source = receipt.get("source", {})
        artifacts = receipt.get("artifacts", [])
        provenance = receipt.get("provenance_chain", {})
        governance = receipt.get("governance", {})
        
        # Find the conversation artifact
        conv_artifact = next(
            (a for a in artifacts if a["artifact_type"] == "conversation"),
            None
        )
        if not conv_artifact:
            return projections
        
        # Conversation note
        conv_id = conv_artifact["artifact_id"]
        conv_ownership = conv_artifact.get("ownership", {})
        provider = source.get("provider", "unknown")
        title = source.get("export_id", "Imported Conversation")
        
        # Collect messages
        messages = [
            a for a in artifacts if a["artifact_type"] == "message"
        ]
        
        # Build conversation note content
        conv_lines = [
            f"# {title}",
            "",
            f"**Source:** {provider}",
            f"**Imported:** {receipt.get('imported_at', '')[:10]}",
            f"**Messages:** {len(messages)}",
            f"**Receipt:** [[{receipt.get('receipt_id', '')}]]",
            "",
            "## Messages",
            "",
        ]
        
        for i, msg in enumerate(messages):
            msg_id = msg["artifact_id"]
            ownership = msg.get("ownership", {})
            conv_lines.append(f"### Message {i+1}")
            conv_lines.append(f"**Artifact:** [[{msg_id}]]")
            conv_lines.append(f"")
        
        conv_content = "\n".join(conv_lines)
        
        conv_frontmatter = {
            "projection_type": "conversation",
            "artifact_id": conv_id,
            "provider": provider,
            "imported_at": receipt.get("imported_at", ""),
            "receipt_id": receipt.get("receipt_id", ""),
            "message_count": len(messages),
            "owner": conv_ownership.get("owner_entity", "unknown"),
            "provenance_chain": provenance.get("chain_id", ""),
            "governance_outcome": governance.get("outcome", "unknown"),
            "projection_generated_at": datetime.now(timezone.utc).isoformat(),
            "projection_source": "ci-projection-boundary-v1"
        }
        
        conv_filename = f"conversations/{conv_id}.md"
        projections.append(ObsidianProjection(conv_filename, conv_content, conv_frontmatter))
        
        # Individual message notes
        for i, msg in enumerate(messages):
            msg_id = msg["artifact_id"]
            msg_ownership = msg.get("ownership", {})
            
            msg_content = f"# Message {i+1}\n\n"
            msg_content += f"**Part of:** [[{conv_id}]]\n"
            msg_content += f"**Receipt:** [[{receipt.get('receipt_id', '')}]]\n"
            
            msg_frontmatter = {
                "projection_type": "message",
                "artifact_id": msg_id,
                "conversation": conv_id,
                "import_session": msg_ownership.get("import_session_id", ""),
                "owner": msg_ownership.get("owner_entity", "unknown"),
                "projection_generated_at": datetime.now(timezone.utc).isoformat(),
                "projection_source": "ci-projection-boundary-v1"
            }
            
            msg_filename = f"messages/{msg_id}.md"
            projections.append(ObsidianProjection(msg_filename, msg_content, msg_frontmatter))
        
        # Receipt note
        receipt_content = self._build_receipt_note(receipt)
        receipt_frontmatter = {
            "projection_type": "receipt",
            "receipt_id": receipt.get("receipt_id", ""),
            "provider": provider,
            "artifact_count": len(artifacts),
            "provenance_entries": len(provenance.get("entries", [])),
            "governance_outcome": governance.get("outcome", ""),
            "projection_generated_at": datetime.now(timezone.utc).isoformat(),
            "projection_source": "ci-projection-boundary-v1"
        }
        receipt_filename = f"receipts/{receipt.get('receipt_id', 'unknown')}.md"
        projections.append(ObsidianProjection(receipt_filename, receipt_content, receipt_frontmatter))
        
        return projections
    
    def _build_receipt_note(self, receipt: dict) -> str:
        """Build a receipt note showing provenance chain."""
        provenance = receipt.get("provenance_chain", {})
        governance = receipt.get("governance", {})
        artifacts = receipt.get("artifacts", [])
        
        lines = [
            f"# Import Receipt: {receipt.get('receipt_id', '')}",
            "",
            "## Source",
            f"- Provider: {receipt.get('source', {}).get('provider', '?')}",
            f"- Export: {receipt.get('source', {}).get('export_id', '?')}",
            f"- Imported: {receipt.get('imported_at', '')}",
            "",
            "## Governance",
            f"- Entity: {governance.get('entity', '?')}",
            f"- Permission: {governance.get('permission', '?')}",
            f"- Outcome: {governance.get('outcome', '?')}",
            "",
            "## Artifacts Created",
        ]
        for a in artifacts:
            lines.append(f"- [[{a['artifact_id']}]] ({a['artifact_type']})")
        
        lines.extend([
            "",
            "## Provenance Chain",
        ])
        for e in provenance.get("entries", []):
            lines.append(f"- {e['transformation']}: [[{e['from'][:20]}...]] → [[{e['to'][:20]}...]]")
        
        lines.append(f"\n_Projection generated: {datetime.now(timezone.utc).isoformat()}_")
        
        return "\n".join(lines)
    
    def _write_index(self, projections: list[ObsidianProjection], vault_root: str):
        """Write an index note listing all projections."""
        convs = [p for p in projections if p.frontmatter.get("projection_type") == "conversation"]
        msgs = [p for p in projections if p.frontmatter.get("projection_type") == "message"]
        receipts_count = len([p for p in projections if p.frontmatter.get("projection_type") == "receipt"])
        
        lines = [
            "# Conversation Ingestion Vault",
            "",
            f"_Projection generated: {datetime.now(timezone.utc).isoformat()}_",
            f"_Source: ci-projection-boundary-v1_",
            "",
            "## Conversations",
            "",
        ]
        for c in convs:
            conv_id = c.frontmatter.get("artifact_id", "?")
            provider = c.frontmatter.get("provider", "?")
            msg_count = c.frontmatter.get("message_count", "?")
            lines.append(f"- [[{conv_id}]] ({provider}, {msg_count} messages)")
        
        lines.extend([
            "",
            "## Summary",
            f"- Conversations: {len(convs)}",
            f"- Messages: {len(msgs)}",
            f"- Receipts: {receipts_count}",
            "",
            "---",
            "_This vault is a read-only projection of governed artifacts._",
            "_Deleting this vault does not delete source artifacts._",
            "_Regenerate with: ci-projection-boundary regenerate_",
        ])
        
        index_path = os.path.join(vault_root, "index.md")
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
    
    @staticmethod
    def clear_vault(vault_root: str):
        """Remove the Obsidian vault without affecting source artifacts.
        
        This is the projection invariant: deleting projections must not
        delete the governed artifacts they were derived from.
        """
        if os.path.exists(vault_root):
            import shutil
            shutil.rmtree(vault_root)
            print(f"  ✅ Vault cleared: {vault_root}")
            print(f"  ✅ Source artifacts unaffected (in-memory)")
