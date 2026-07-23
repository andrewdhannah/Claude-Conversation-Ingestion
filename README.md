# Claude Conversation Ingestion

**Status:** Planning — reference SDK add-on
**Repository:** andrewdhannah/Claude-Conversation-Ingestion

---

## Purpose

Reference implementation add-on for the Librarian SDK. Imports Claude and ChatGPT export data into a governed, searchable, provenance-tracked format. Exercises every SDK boundary: capability declaration, manifest, lifecycle, health, storage, migrations, provenance, and evidence.

## Capabilities

| Capability | Description |
|-----------|-------------|
| `conversation.import` | Import Claude/ChatGPT export JSON |
| `conversation.search` | Full-text search across conversations |
| `conversation.export` | Export as Obsidian-compatible vault ZIP |

## Architecture

```
Claude/ChatGPT Export
         ↓
Private DB (conversation.db)
         ↓
Provenance + Evidence + Receipt
         ↓
Obsidian Vault (downloadable ZIP)
         ↓
Search index
```

## Project Detection

Built-in keyword matching routes conversations to projects:

- TheLibrarian, AgentBridge, FlightPlan, QAPilot, SessionSpine
- WorkPacketCompiler, AgileInABox, SoftwareConductor, Cowork
- LegacyBridge, VulkanPolaris, GuardianAngel, VeriTax
- CottageApp, CarbideFrame

## Governance

All operations flow through the SDK governance client:

```
Entity → Decision → Permission → Custody → Execute → Evidence → Receipt
```

## Prerequisites

- Librarian SDK (librarian-sdk crate)
- ENTITY-001, DECISIONS-001, PERMISSIONS-001
- UF-001 (MCP server) for external invocation

## License

MIT
