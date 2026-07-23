"""
Context package builder — minimized model input per capability.

Design rule: The provider declares what it needs.
              The Librarian decides what it receives.

A context package is a minimized, governed subset of the knowledge store
assembled for a specific capability invocation. It is a projection, not
a copy — deleting a context package does not delete source artifacts.

Context budget concept (future):
  Providers can declare context_requirements in their manifest:
  {
    "minimum": ["task", "current_decisions"],
    "optional": ["related_artifacts"],
    "maximum_tokens": 16000
  }
  The Librarian uses this to size the context package appropriately.
"""

from datetime import datetime, timezone
from typing import Optional
import json
import uuid


class ContextPackage:
    """A minimized context package for model consumption."""
    
    def __init__(self, task: str, capability: str,
                 model_tier: str = "reasoning",
                 contracts: Optional[list[dict]] = None,
                 decisions: Optional[list[dict]] = None,
                 constraints: Optional[list[str]] = None,
                 artifacts: Optional[list[str]] = None,
                 provenance: Optional[list[dict]] = None,
                 previous_failures: Optional[list[str]] = None,
                 token_budget: int = 16000):
        self.package_id = f"ci-context-{uuid.uuid4().hex[:12]}"
        self.generated_at = datetime.now(timezone.utc).isoformat()
        self.task = task
        self.capability = capability
        self.model_tier = model_tier
        self.contracts = contracts or []
        self.decisions = decisions or []
        self.constraints = constraints or []
        self.artifact_refs = artifacts or []
        self.provenance = provenance or []
        self.previous_failures = previous_failures or []
        self.token_budget = token_budget
        self.estimated_tokens = self._estimate_tokens()
    
    def _estimate_tokens(self) -> int:
        """Rough token estimate (4 chars ≈ 1 token).
        
        Estimates from raw fields only — avoids circular dependency
        between estimated_tokens and to_dict().
        """
        estimate = len(self.task) + len(self.capability)
        for c in self.contracts:
            estimate += len(json.dumps(c))
        for d in self.decisions:
            estimate += len(json.dumps(d))
        for c in self.constraints or []:
            estimate += len(c)
        for a in self.artifact_refs or []:
            estimate += len(a)
        for p in self.provenance or []:
            estimate += len(json.dumps(p))
        return estimate // 4 + 100  # Base overhead
    
    def to_dict(self) -> dict:
        return {
            "package_schema": "ci-context-package-v1",
            "package_id": self.package_id,
            "generated_at": self.generated_at,
            "task": self.task,
            "capability": self.capability,
            "model_tier": self.model_tier,
            "token_budget": self.token_budget,
            "estimated_tokens": self.estimated_tokens,
            "contracts": self.contracts,
            "decisions": self.decisions,
            "constraints": self.constraints,
            "artifact_refs": self.artifact_refs,
            "provenance": self.provenance[:5],  # Brief provenance for context
            "previous_failures": self.previous_failures
        }
    
    def is_within_budget(self) -> bool:
        """Check if estimated tokens are within budget."""
        return self.estimated_tokens <= self.token_budget


class ContextPackageBuilder:
    """Builds minimized context packages from governed artifacts.
    
    Selection policy (future):
      The provider declares minimum/optional context requirements.
      The Librarian evaluates what is authorized and assembles the package.
    
    Current implementation:
      Creates a bounded package from available receipts and metadata.
    """
    
    def build_for_capability(self, task: str, capability: str,
                              model_tier: str = "reasoning",
                              receipts: Optional[list] = None,
                              constraints: Optional[list[str]] = None,
                              token_budget: int = 16000) -> ContextPackage:
        """Build a context package for a specific capability invocation."""
        
        # Extract contracts from receipts
        contracts = []
        decisions = []
        provenance = []
        
        if receipts:
            for r in receipts:
                gov = r.get("governance", {})
                decisions.append({
                    "decision_id": gov.get("decision_id", ""),
                    "outcome": gov.get("outcome", ""),
                    "permission": gov.get("permission", "")
                })
                prov = r.get("provenance_chain", {})
                provenance.append({
                    "chain_id": prov.get("chain_id", ""),
                    "source": prov.get("source_export", {}).get("provider", ""),
                    "entries": len(prov.get("entries", []))
                })
        
        # Build minimal package
        pkg = ContextPackage(
            task=task,
            capability=capability,
            model_tier=model_tier,
            contracts=contracts,
            decisions=decisions,
            constraints=constraints or [],
            artifacts=[str(r.get("receipt_id", "")) for r in (receipts or [])],
            provenance=provenance,
            token_budget=token_budget
        )
        
        return pkg
    
    def build_minimal(self, task: str, capability: str) -> ContextPackage:
        """Build the smallest possible context package (local model).
        
        For local/small models — only task and capability, no history.
        """
        return ContextPackage(
            task=task,
            capability=capability,
            model_tier="local",
            contracts=[],
            decisions=[],
            constraints=["Follow the provider manifest contract"],
            artifacts=[],
            provenance=[],
            token_budget=8000  # Smaller budget for local models
        )
    
    def build_reasoning(self, task: str, capability: str,
                         receipts: list) -> ContextPackage:
        """Build a reasoning context package (frontier model).
        
        Includes decisions, constraints, and provenance context.
        """
        return self.build_for_capability(
            task=task,
            capability=capability,
            model_tier="reasoning",
            receipts=receipts,
            token_budget=16000
        )
    
    def build_review(self, task: str, capability: str,
                      receipts: list) -> ContextPackage:
        """Build a review context package (validation).
        
        Includes everything for deterministic validation.
        """
        return self.build_for_capability(
            task=task,
            capability=capability,
            model_tier="review",
            receipts=receipts,
            token_budget=32000  # Largest budget for review
        )
