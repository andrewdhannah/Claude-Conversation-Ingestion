"""
Claude export format parser.

Parses the JSON export format from claude.ai (Settings → Export Data).
The export is a single JSON file containing an array of conversations
with their messages in a tree structure.
"""

from datetime import datetime, timezone
from typing import Optional
import json
import hashlib


class ClaudeMessage:
    """A single message from a Claude conversation."""
    
    def __init__(self, uuid: str, sender: str, content: str,
                 created_at: str, parent_uuid: Optional[str] = None):
        self.uuid = uuid
        self.sender = sender  # "human" or "assistant"
        self.content = content
        self.created_at = created_at
        self.parent_uuid = parent_uuid
    
    @property
    def is_user(self) -> bool:
        return self.sender == "human"
    
    @property
    def is_assistant(self) -> bool:
        return self.sender == "assistant"
    
    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "sender": self.sender,
            "content_preview": self.content[:200],
            "content_length": len(self.content),
            "created_at": self.created_at,
            "parent_uuid": self.parent_uuid
        }


class ClaudeConversation:
    """A single conversation from a Claude export."""
    
    def __init__(self, uuid: str, name: str, created_at: str,
                 updated_at: str, messages: list[ClaudeMessage]):
        self.uuid = uuid
        self.name = name or "Untitled Conversation"
        self.created_at = created_at
        self.updated_at = updated_at
        self.messages = messages
    
    @property
    def message_count(self) -> int:
        return len(self.messages)
    
    @property
    def user_message_count(self) -> int:
        return sum(1 for m in self.messages if m.is_user)
    
    @property
    def assistant_message_count(self) -> int:
        return sum(1 for m in self.messages if m.is_assistant)
    
    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": self.message_count,
            "messages": [m.to_dict() for m in self.messages]
        }


class ClaudeParser:
    """Parses Claude.ai export JSON into structured conversation objects."""
    
    def parse_file(self, filepath: str) -> list[ClaudeConversation]:
        """Parse a Claude export JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return self.parse_json(data)
    
    def parse_json(self, data: dict) -> list[ClaudeConversation]:
        """Parse a Claude export JSON structure."""
        conversations = []
        raw = data.get("conversations", data if isinstance(data, list) else [])
        
        if isinstance(raw, dict):
            raw = [raw]
        
        for conv in raw:
            conv_uuid = conv.get("uuid", conv.get("id", ""))
            conv_name = conv.get("name", "")
            conv_created = conv.get("created_at", "")
            conv_updated = conv.get("updated_at", "")
            
            messages = []
            for msg in conv.get("chat_messages", []):
                msg_uuid = msg.get("uuid", msg.get("id", ""))
                sender = msg.get("sender", "unknown")
                content = self._extract_content(msg)
                created_at = msg.get("created_at", "")
                parent_uuid = msg.get("parent_message_uuid")
                
                messages.append(ClaudeMessage(
                    uuid=msg_uuid,
                    sender=sender,
                    content=content,
                    created_at=created_at,
                    parent_uuid=parent_uuid
                ))
            
            conversations.append(ClaudeConversation(
                uuid=conv_uuid,
                name=conv_name,
                created_at=conv_created,
                updated_at=conv_updated,
                messages=messages
            ))
        
        return conversations
    
    def _extract_content(self, msg: dict) -> str:
        """Extract text content from a message, handling various formats."""
        content = msg.get("content", "")
        if isinstance(content, list):
            parts = []
            for c in content:
                if isinstance(c, dict):
                    parts.append(c.get("text", c.get("content", str(c))))
                else:
                    parts.append(str(c))
            return "\n".join(parts)
        return content if isinstance(content, str) else str(content)
    
    @staticmethod
    def compute_hash(conversation: ClaudeConversation) -> str:
        """Compute a deterministic content hash for deduplication."""
        content_str = json.dumps({
            "uuid": conversation.uuid,
            "messages": [(m.uuid, m.sender, m.content) for m in conversation.messages]
        }, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()
