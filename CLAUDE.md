# Claude Conversation Ingestion — CLAUDE.md

**Project:** `claude-conversation-ingestion`
**Purpose:** Reference SDK add-on for importing Claude/ChatGPT exports into governed, provenance-tracked knowledge store.

## Current State

**Lifecycle phase:** foundation
**Contract:** CI-LIBRARIAN-CONTRACT-v1

## Key Sources

- **Identity:** `docs/identity/PROJECT-IDENTITY.md`
- **Contracts:** `docs/contracts/CI-LIBRARIAN-CONTRACT-v1.json`
- **Provider manifest:** `mcp/capabilities.json`
- **Schemas:** `docs/schemas/ci-import-receipt.schema.json`, `docs/schemas/ci-artifact.schema.json`, `docs/schemas/ci-provenance-chain.schema.json`

## Architecture

```
Conversation Export
        ↓
Import Handler (src/import/handler.py)
        ↓
Provenance Chain (src/provenance/chain.py)
        ↓
Artifact Ownership (src/artifacts/ownership.py)
        ↓
Import Receipt (ci-import-receipt-v1)
```

## Governance

All operations flow through the SDK governance client:

```
Entity → Decision → Permission → Custody → Execute → Evidence → Receipt
```

## Declared Capabilities

| Capability | Risk | Tool | Status |
|-----------|------|------|--------|
| `conversation.import` | R1 | `ci_import` | Foundation |
| `conversation.search` | R0 | `ci_search` | Foundation |
| `conversation.export` | R1 | `ci_export` | Foundation |

## External Reference

Librarian governance docs at `../active/librarian/docs/governance/` and `../active/librarian/docs/schemas/` are authoritative.

## Non-Goals (Foundation Phase)

- RAG / vector search
- Obsidian vault projection
- Full-text search index
- UI components
