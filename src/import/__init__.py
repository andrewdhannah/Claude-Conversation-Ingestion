"""
Conversation import handler.

Every import produces:
1. A provenance chain (source_export → artifacts)
2. Artifact ownership records
3. An import receipt (governance evidence)

The import handler does NOT perform RAG or Obsidian projection.
It only establishes the authority chain for imported data.
"""

from .handler import ImportHandler, ImportReceipt
