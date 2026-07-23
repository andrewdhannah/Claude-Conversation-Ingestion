"""
Provenance chain for conversation ingestion.

Tracks the lifecycle of conversation artifacts from source export
through import, extraction, derivation, and linking.

Chain invariants:
1. Every transformation is recorded as a chain entry
2. Every entry has a from/to and transformation type
3. Source export is the root of every chain
4. Terminal artifacts are the most derived form
"""

from .chain import ProvenanceChain, ProvenanceEntry
