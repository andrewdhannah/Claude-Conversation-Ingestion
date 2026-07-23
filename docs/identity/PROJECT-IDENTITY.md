# Project Identity — Claude Conversation Ingestion

**Status:** Foundation
**Version:** 0.1.0
**Classification:** SDK add-on provider (knowledge_custody_provider)
**Domain:** knowledge_custody
**Contract:** CI-LIBRARIAN-CONTRACT-v1

---

## Purpose

Reference SDK add-on that imports Claude and ChatGPT conversation exports into a governed, provenance-tracked knowledge store. Exercises every SDK boundary: capability declaration, manifest, lifecycle, health, storage, migrations, provenance, and evidence.

## Authority Chain

All operations flow through the librarian SDK governance client:

```
Entity → Decision → Permission → Custody → Execute → Evidence → Receipt
```

## Declared Capabilities

| Capability | Risk | Tool | Description |
|-----------|------|------|-------------|
| `conversation.import` | R1 | `ci_import` | Import Claude/ChatGPT export JSON |
| `conversation.search` | R0 | `ci_search` | Full-text search across conversations |
| `conversation.export` | R1 | `ci_export` | Export as provenance-bundled archive |

## Governance

- All capabilities are advisory-only in discovery
- R1 capabilities require permission validation before execution
- Every import produces evidence + receipt
- Artifact ownership is traced to source conversation and import session

## Dependencies

- Librarian SDK (`librarian-sdk`)
- `librarian-node` for MCP surface exposure
- `working-bibliography-extension` for shared artifact model
