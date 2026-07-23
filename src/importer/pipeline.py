"""
Import pipeline — processes real Claude and ChatGPT exports.

Flow:
  Export File → Detect Format → Parse → Hash → Normalize → Provenance → Receipt

The pipeline is the real-data counterpart to the handler's synthetic proof.
It produces the same artifact types but from actual export content.
"""

from datetime import datetime, timezone
from typing import Optional
import json
import os
import hashlib
import uuid

from src.importer.claude_parser import ClaudeParser, ClaudeConversation
from src.importer.chatgpt_parser import ChatGPTParser, ChatGPTConversation
from src.artifacts.ownership import ArtifactOwnership, OwnershipRecord
from src.provenance.chain import ProvenanceChain, ProvenanceEntry
from src.importer.handler import ImportHandler, ImportReceipt


class NormalizedConversation:
    """A provider-agnostic normalized conversation."""
    
    def __init__(self, source_provider: str, source_id: str,
                 title: str, created_at: str, updated_at: str,
                 messages: list[dict], content_hash: str):
        self.source_provider = source_provider
        self.source_id = source_id
        self.title = title
        self.created_at = created_at
        self.updated_at = updated_at
        self.messages = messages
        self.content_hash = content_hash
    
    @property
    def message_count(self) -> int:
        return len(self.messages)


class ImportPipeline:
    """Processes real conversation exports through the full authority chain."""
    
    def __init__(self, owner_entity: str = "default"):
        self.owner_entity = owner_entity
        self.seen_hashes: set[str] = set()  # For duplicate detection
        self.parser = ClaudeParser()
        self.chatgpt_parser = ChatGPTParser()
    
    def detect_format(self, filepath: str) -> str:
        """Detect whether a file is Claude or ChatGPT format."""
        with open(filepath, 'r', encoding='utf-8') as f:
            preview = f.read(4096)
            f.seek(0)
        
        preview_lower = preview.lower()
        
        # Claude format has "chat_messages" and "sender" fields
        if '"chat_messages"' in preview_lower or '"sender"' in preview_lower:
            return "claude"
        
        # ChatGPT format has "mapping" and "author.role" structure
        if '"mapping"' in preview_lower or '"create_time"' in preview_lower:
            return "chatgpt"
        
        # Try to detect by structure
        try:
            data = json.loads(preview)
            if isinstance(data, dict) and "conversations" in data:
                return "claude"
            if isinstance(data, list):
                return "chatgpt"
        except json.JSONDecodeError:
            pass
        
        raise ValueError(f"Cannot detect export format for: {filepath}")
    
    def compute_file_hash(self, filepath: str) -> str:
        """Compute SHA-256 hash of the raw export file."""
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    
    def is_duplicate(self, content_hash: str) -> bool:
        """Check if a content hash has already been imported."""
        return content_hash in self.seen_hashes
    
    def normalize_claude(self, conv: ClaudeConversation) -> NormalizedConversation:
        """Normalize a parsed Claude conversation."""
        messages = []
        for msg in conv.messages:
            messages.append({
                "role": "user" if msg.is_user else "assistant",
                "content": msg.content,
                "timestamp": msg.created_at,
                "id": msg.uuid
            })
        
        content_hash = ClaudeParser.compute_hash(conv)
        
        return NormalizedConversation(
            source_provider="claude",
            source_id=conv.uuid,
            title=conv.name,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=messages,
            content_hash=content_hash
        )
    
    def normalize_chatgpt(self, conv: ChatGPTConversation) -> NormalizedConversation:
        """Normalize a parsed ChatGPT conversation."""
        messages = []
        for msg in conv.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": str(msg.create_time),
                "id": msg.node_id
            })
        
        content_hash = ChatGPTParser.compute_hash(conv)
        
        return NormalizedConversation(
            source_provider="chatgpt",
            source_id=conv.conversation_id,
            title=conv.title,
            created_at=str(conv.create_time),
            updated_at=str(conv.update_time),
            messages=messages,
            content_hash=content_hash
        )
    
    def process_file(self, filepath: str) -> list[ImportReceipt]:
        """Process a single export file through the full pipeline.
        
        Returns a list of ImportReceipts (one per conversation).
        """
        file_hash = self.compute_file_hash(filepath)
        fmt = self.detect_format(filepath)
        filename = os.path.basename(filepath)
        
        receipts = []
        
        if fmt == "claude":
            conversations = self.parser.parse_file(filepath)
            for conv in conversations:
                receipt = self._process_conversation(conv, "claude", file_hash, filename)
                if receipt:
                    receipts.append(receipt)
        
        elif fmt == "chatgpt":
            conversations = self.chatgpt_parser.parse_file(filepath)
            for conv in conversations:
                receipt = self._process_conversation(conv, "chatgpt", file_hash, filename)
                if receipt:
                    receipts.append(receipt)
        
        return receipts
    
    def _process_conversation(self, conv, provider: str,
                               file_hash: str, filename: str) -> Optional[ImportReceipt]:
        """Process a single conversation through the authority chain."""
        
        # Normalize
        if provider == "claude":
            normalized = self.normalize_claude(conv)
            source_id = conv.uuid
        else:
            normalized = self.normalize_chatgpt(conv)
            source_id = conv.conversation_id
        
        # Duplicate detection
        if self.is_duplicate(normalized.content_hash):
            return None
        
        self.seen_hashes.add(normalized.content_hash)
        
        # Create provenance chain
        source_export_id = f"export-{os.path.splitext(filename)[0]}-{source_id[:8]}"
        chain = ProvenanceChain(provider, source_export_id, file_hash)
        
        # Create ownership
        ownership = ArtifactOwnership(
            owner_entity=self.owner_entity,
            import_session_id=chain.import_session_id
        )
        
        # Register conversation artifact (root)
        conv_artifact = ownership.register_artifact(
            artifact_type="conversation",
            source_provider=provider,
            source_export_id=source_export_id,
            provenance_id=chain.chain_id
        )
        
        chain.add_entry(
            from_id="source_export",
            to_id=conv_artifact.artifact_id,
            transformation="import",
            detail=f"Imported {provider} conversation: {normalized.title[:80]}",
            evidence_ref=f"hash:{normalized.content_hash[:16]}"
        )
        
        # Register each message as a derived artifact
        for i, msg in enumerate(normalized.messages):
            msg_artifact = ownership.register_artifact(
                artifact_type="message",
                source_provider=provider,
                source_export_id=source_export_id,
                provenance_id=chain.chain_id
            )
            
            chain.add_entry(
                from_id=conv_artifact.artifact_id,
                to_id=msg_artifact.artifact_id,
                transformation="extract",
                detail=f"Message {i+1}: {msg['role']} ({len(msg['content'])} chars)",
            )
        
        # Detect project references and create entity artifacts
        project_keywords = [
            "librarian", "agentbridge", "flightplan", "qapilot",
            "carbideframe", "openwork", "scrummaster", "workpacket"
        ]
        
        for kw in project_keywords:
            title_lower = normalized.title.lower()
            content_lower = " ".join(m.get("content", "") for m in normalized.messages).lower()
            
            if kw in title_lower or kw in content_lower:
                entity_artifact = ownership.register_artifact(
                    artifact_type="project_match",
                    source_provider=provider,
                    source_export_id=source_export_id,
                    provenance_id=chain.chain_id
                )
                
                chain.add_entry(
                    from_id=conv_artifact.artifact_id,
                    to_id=entity_artifact.artifact_id,
                    transformation="derive",
                    detail=f"Project reference detected: {kw}"
                )
        
        # Build governance outcome
        governance = {
            "entity": self.owner_entity,
            "decision_id": f"ci-decision-{uuid.uuid4().hex[:12]}",
            "permission": "entity.self.artifact.register",
            "outcome": "allowed"
        }
        
        # Build receipt
        receipt = ImportReceipt(
            receipt_id=f"ci-receipt-{uuid.uuid4().hex[:12]}",
            imported_at=datetime.now(timezone.utc).isoformat(),
            source={
                "provider": provider,
                "export_id": source_export_id,
                "exported_at": normalized.created_at,
                "file_hash": file_hash,
                "filename": filename,
                "content_hash": normalized.content_hash
            },
            artifacts=ownership.get_artifacts(),
            provenance_chain=chain.to_dict(),
            governance=governance,
            evidence_refs=[
                f"provenance:{chain.chain_id}",
                f"ownership:{ownership.import_session_id}",
                f"hash:{normalized.content_hash[:16]}"
            ]
        )
        
        return receipt
    
    def process_directory(self, dirpath: str) -> list[ImportReceipt]:
        """Process all export files in a directory."""
        all_receipts = []
        for fname in sorted(os.listdir(dirpath)):
            if fname.endswith(".json"):
                fpath = os.path.join(dirpath, fname)
                try:
                    receipts = self.process_file(fpath)
                    all_receipts.extend(receipts)
                except Exception as e:
                    print(f"  ⚠️  Skipped {fname}: {e}")
        return all_receipts
