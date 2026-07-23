"""
Projection boundary module for Conversation Ingestion.

All projections are READ-ONLY derivatives of governed artifacts.
Projections do not own data. They transform it for consumption.

Invariant: Deleting a projection must never delete the source artifact.
Invariant: Regeneration from source must produce identical output.

Projection types:
  Obsidian Vault   — Markdown notes with wiki-link cross-references
  Context Package  — Minimized model input (per capability/model type)
  RAG Index        — Searchable vector/text index (stub)

The projection boundary is the last layer before external consumption.
Below this boundary: governed artifacts with ownership, provenance, receipts.
Above this boundary: transient views optimized for specific consumers.
"""

from .obsidian import ObsidianProjection, ObsidianVaultGenerator
from .context_package import ContextPackageBuilder, ContextPackage
from .rag_index import RAGIndexProjection, RAGIndexGenerator
