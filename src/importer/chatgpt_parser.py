"""
ChatGPT export format parser.

Parses the JSON export format from chat.openai.com (Settings → Export Data).
The export contains a conversations.json file with an array of conversations
that use a node-based message mapping structure.
"""

from datetime import datetime, timezone
from typing import Optional
import json
import hashlib


class ChatGPTMessage:
    """A single message from a ChatGPT conversation."""
    
    def __init__(self, node_id: str, role: str, content: str,
                 create_time: float, parent_id: Optional[str] = None):
        self.node_id = node_id
        self.role = role  # "user", "assistant", "system", "tool"
        self.content = content
        self.create_time = create_time
        self.parent_id = parent_id
    
    @property
    def is_user(self) -> bool:
        return self.role == "user"
    
    @property
    def is_assistant(self) -> bool:
        return self.role == "assistant"
    
    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "role": self.role,
            "content_preview": self.content[:200],
            "content_length": len(self.content),
            "create_time": self.create_time,
            "parent_id": self.parent_id
        }


class ChatGPTConversation:
    """A single conversation from a ChatGPT export."""
    
    def __init__(self, conversation_id: str, title: str,
                 create_time: float, update_time: float,
                 messages: list[ChatGPTMessage]):
        self.conversation_id = conversation_id
        self.title = title or "Untitled Conversation"
        self.create_time = create_time
        self.update_time = update_time
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
            "conversation_id": self.conversation_id,
            "title": self.title,
            "create_time": self.create_time,
            "update_time": self.update_time,
            "message_count": self.message_count,
            "messages": [m.to_dict() for m in self.messages]
        }


class ChatGPTParser:
    """Parses ChatGPT export JSON into structured conversation objects."""
    
    def parse_file(self, filepath: str) -> list[ChatGPTConversation]:
        """Parse a ChatGPT export JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return self.parse_json(data)
    
    def parse_json(self, data: list | dict) -> list[ChatGPTConversation]:
        """Parse a ChatGPT export JSON structure."""
        conversations = []
        raw_list = data if isinstance(data, list) else [data]
        
        for conv in raw_list:
            conv_id = conv.get("conversation_id", conv.get("id", ""))
            title = conv.get("title", "")
            create_time = conv.get("create_time", 0)
            update_time = conv.get("update_time", 0)
            
            # Extract messages from the mapping structure
            mapping = conv.get("mapping", {})
            messages = self._extract_messages(mapping)
            
            conversations.append(ChatGPTConversation(
                conversation_id=conv_id,
                title=title,
                create_time=create_time,
                update_time=update_time,
                messages=messages
            ))
        
        return conversations
    
    def _extract_messages(self, mapping: dict) -> list[ChatGPTMessage]:
        """Extract ordered messages from the mapping dict (tree structure)."""
        # Build the list by walking the tree from root to leaves
        nodes = {}
        roots = []
        
        for node_id, node in mapping.items():
            msg_data = node.get("message")
            if not msg_data:
                continue
            
            parent_id = node.get("parent")
            if parent_id == "None" or parent_id is None:
                parent_id = None
            
            role = msg_data.get("author", {}).get("role", "unknown")
            content = self._extract_content(msg_data.get("content", {}))
            create_time = msg_data.get("create_time", 0)
            
            nodes[node_id] = (node_id, role, content, create_time, parent_id)
            
            if parent_id is None:
                roots.append(node_id)
        
        # Order by walking from root (BFS)
        ordered = []
        visited = set()
        
        def walk(node_id):
            if node_id in visited or node_id not in nodes:
                return
            visited.add(node_id)
            nid, role, content, ct, parent = nodes[node_id]
            ordered.append(ChatGPTMessage(nid, role, content, ct, parent))
            
            # Find children
            for nid2, node2 in nodes.items():
                if node2[4] == node_id:
                    walk(nid2)
        
        # If no root found, try to find one
        if not roots and nodes:
            # Pick the first node without a parent in the set
            all_ids = set(nodes.keys())
            all_parents = set(n[4] for n in nodes.values() if n[4])
            remaining = all_ids - all_parents
            if remaining:
                roots = [list(remaining)[0]]
        
        for root in roots:
            walk(root)
        
        # Fallback: if ordering failed, return in insertion order
        if not ordered:
            ordered = [ChatGPTMessage(nid, r, c, ct, p) 
                      for nid, r, c, ct, p in nodes.values()]
        
        return ordered
    
    def _extract_content(self, content: dict) -> str:
        """Extract text content from ChatGPT's nested content structure."""
        parts = content.get("parts", [])
        text_parts = []
        for part in parts:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict):
                text_parts.append(part.get("text", str(part)))
            else:
                text_parts.append(str(part))
        return "\n".join(text_parts)
    
    @staticmethod
    def compute_hash(conversation: ChatGPTConversation) -> str:
        """Compute a deterministic content hash for deduplication."""
        content_str = json.dumps({
            "conversation_id": conversation.conversation_id,
            "messages": [(m.node_id, m.role, m.content) for m in conversation.messages]
        }, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()
