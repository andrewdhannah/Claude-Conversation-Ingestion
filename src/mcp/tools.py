"""
Tool definitions for the Conversation Ingestion MCP interface.

Each tool corresponds to a declared capability in the provider manifest.
Current state: foundation — tool implementations are stubs pending
import handler completion.
"""

# Tool definitions for tools/list
TOOL_DEFINITIONS = [
    {
        "name": "ci_import",
        "description": "Import a Claude or ChatGPT conversation export",
        "capability": "conversation.import",
        "risk": "R1",
        "inputSchema": {
            "type": "object",
            "properties": {
                "provider": {"type": "string", "enum": ["claude", "chatgpt"]},
                "export_id": {"type": "string"},
                "content": {"type": "string", "description": "Raw export JSON content"}
            },
            "required": ["provider", "export_id", "content"]
        }
    },
    {
        "name": "ci_search",
        "description": "Full-text search across imported conversations",
        "capability": "conversation.search",
        "risk": "R0",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 20}
            },
            "required": ["query"]
        }
    },
    {
        "name": "ci_export",
        "description": "Export conversations as provenance-bundled archive",
        "capability": "conversation.export",
        "risk": "R1",
        "inputSchema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["provenance_bundle", "receipt_package"]},
                "artifact_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional — export specific artifacts"
                }
            },
            "required": ["format"]
        }
    }
]


def get_active_tools() -> list:
    """Return tool definitions for declared capabilities.
    
    Only returns tools for capabilities in active lifecycle state.
    """
    return TOOL_DEFINITIONS
