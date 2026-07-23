"""
Context package builder — CI-004 Controlled Disclosure Boundary.

CI-004 formalizes what CI-003 proved experimentally: model-independent
context packages with auditable disclosure records.

The key additions over CI-003:
  - Why was each artifact included? (permission_basis)
  - Why was each artifact excluded? (exclusion_reason)
  - Which model class received it? (target.model_class)
  - Auditable evidence trail (evidence_refs)

Design rule:
  The model does not decide what it knows.
  The Librarian decides what context package it receives.
"""

from datetime import datetime, timezone
from typing import Optional
import json
import uuid


class DisclosureRecord:
    """Records why an artifact was included or excluded from a context package."""
    
    def __init__(self):
        self.included: list[dict] = []  # {artifact_id, reason, permission_basis}
        self.excluded: list[dict] = []  # {artifact_id, reason}
    
    def include(self, artifact_id: str, reason: str,
                permission_basis: str = "entity.self.artifact.read"):
        """Record an artifact as included with disclosure reason."""
        self.included.append({
            "artifact_id": artifact_id,
            "reason": reason,
            "permission_basis": permission_basis
        })
    
    def exclude(self, artifact_id: str, reason: str):
        """Record an artifact as excluded with justification."""
        self.excluded.append({
            "artifact_id": artifact_id,
            "reason": reason
        })
    
    def to_dict(self) -> dict:
        return {
            "included_artifacts": self.included,
            "excluded_artifacts": self.excluded
        }


class ContextPackage:
    """A governed context package with full disclosure audit trail.
    
    Answers: 'What did the AI know when it made this decision?'
    """
    
    def __init__(self, task: str, capability: str,
                 model_class: str = "reasoning",
                 contracts: Optional[list[dict]] = None,
                 decisions: Optional[list[dict]] = None,
                 constraints: Optional[list[str]] = None,
                 provenance: Optional[list[dict]] = None,
                 token_budget: int = 16000):
        self.package_id = f"ci-context-{uuid.uuid4().hex[:12]}"
        self.generated_at = datetime.now(timezone.utc).isoformat()
        self.task = task
        self.capability = capability
        self.model_class = model_class
        self.contracts = contracts or []
        self.decisions = decisions or []
        self.constraints = constraints or []
        self.provenance = provenance or []
        self.token_budget = token_budget
        self.disclosure = DisclosureRecord()
        self.evidence_refs: list[str] = []
    
    def _estimate_tokens(self) -> int:
        """Estimate tokens from raw fields (no circular dependency)."""
        estimate = len(self.task) + len(self.capability)
        for c in self.contracts:
            estimate += len(json.dumps(c))
        for d in self.decisions:
            estimate += len(json.dumps(d))
        for c in self.constraints or []:
            estimate += len(c)
        return estimate // 4 + 100
    
    @property
    def estimated_tokens(self) -> int:
        return self._estimate_tokens()
    
    def is_within_budget(self) -> bool:
        return self.estimated_tokens <= self.token_budget
    
    def to_dict(self) -> dict:
        """Serialize to ci-context-package-v1 schema."""
        return {
            "package_schema": "ci-context-package-v1",
            "package_id": self.package_id,
            "generated_at": self.generated_at,
            "target": {
                "model_class": self.model_class,
                "capability": self.capability,
                "task": self.task,
                "token_budget": self.token_budget
            },
            "disclosure": {
                "included_artifacts": self.disclosure.included,
                "excluded_artifacts": self.disclosure.excluded,
                "estimated_tokens": self.estimated_tokens,
                "within_budget": self.is_within_budget()
            },
            "context": {
                "task": self.task,
                "capability": self.capability,
                "contracts": self.contracts,
                "constraints": self.constraints,
                "decisions": self.decisions,
                "provenance": self.provenance[:5]
            },
            "evidence_refs": self.evidence_refs
        }


class ContextPackageBuilder:
    """Builds context packages with auditable disclosure records.
    
    Each package records:
      - Which artifacts were included and why (permission_basis)
      - Which artifacts were excluded and why (exclusion_reason)
      - Which model class received the package
      - Evidence references for the entire disclosure
    """
    
    def __init__(self):
        self.total_packages_built = 0
    
    def build_minimal(self, task: str, capability: str) -> ContextPackage:
        """Smallest possible context package (local/draft model).
        
        Only task and capability — no history, no decisions, no provenance.
        Context budget: 8000 tokens.
        """
        pkg = ContextPackage(
            task=task,
            capability=capability,
            model_class="local",
            token_budget=8000
        )
        pkg.constraints = ["Follow the provider manifest contract"]
        
        pkg.disclosure.include(
            artifact_id="task",
            reason="Required for all model classes — defines the work to be done",
            permission_basis="entity.self.task.define"
        )
        pkg.disclosure.include(
            artifact_id="capability",
            reason="Required for all model classes — defines the execution contract",
            permission_basis="entity.self.capability.execute"
        )
        pkg.disclosure.exclude(
            artifact_id="decisions",
            reason="Local model does not require decision history for structured generation tasks"
        )
        pkg.disclosure.exclude(
            artifact_id="provenance",
            reason="Local model operates on current task only; provenance is governance-layer concern"
        )
        
        pkg.evidence_refs = [
            f"constraint:ci-minimal-context-{task[:16]}"
        ]
        self.total_packages_built += 1
        return pkg
    
    def build_reasoning(self, task: str, capability: str,
                         receipts: list) -> ContextPackage:
        """Reasoning context package (frontier model).
        
        Includes decisions, constraints, and provenance context.
        Context budget: 16000 tokens.
        """
        pkg = ContextPackage(
            task=task,
            capability=capability,
            model_class="reasoning",
            token_budget=16000
        )
        
        # Extract governance context from receipts
        seen_decisions = set()
        for r in receipts:
            gov = r.get("governance", {})
            decision_id = gov.get("decision_id", "")
            if decision_id and decision_id not in seen_decisions:
                seen_decisions.add(decision_id)
                decision = {
                    "decision_id": decision_id,
                    "outcome": gov.get("outcome", ""),
                    "permission": gov.get("permission", "")
                }
                pkg.decisions.append(decision)
                pkg.disclosure.include(
                    artifact_id=decision_id,
                    reason=f"Related decision for {capability} — informs current reasoning",
                    permission_basis=gov.get("permission", "entity.self.artifact.read")
                )
            
            prov = r.get("provenance_chain", {})
            pkg.provenance.append({
                "chain_id": prov.get("chain_id", ""),
                "source": prov.get("source_export", {}).get("provider", ""),
                "entries": len(prov.get("entries", []))
            })
        
        pkg.disclosure.exclude(
            artifact_id="raw_messages",
            reason="Message content excluded from context — only metadata and decisions provided"
        )
        pkg.disclosure.exclude(
            artifact_id="full_provenance_detail",
            reason="Provenance summarized to chain metadata; full detail available through evidence_refs"
        )
        
        pkg.evidence_refs = [
            f"disclosure:ci-reasoning-{pkg.package_id[:12]}",
            f"decisions:{len(seen_decisions)}"
        ]
        self.total_packages_built += 1
        return pkg
    
    def build_review(self, task: str, capability: str,
                      receipts: list) -> ContextPackage:
        """Review context package (validation/governance).
        
        Largest context budget (32000 tokens) for deterministic validation.
        Includes most comprehensive disclosure.
        """
        pkg = ContextPackage(
            task=task,
            capability=capability,
            model_class="review",
            token_budget=32000
        )
        
        # Full governance context
        seen_decisions = set()
        for r in receipts:
            gov = r.get("governance", {})
            decision_id = gov.get("decision_id", "")
            if decision_id and decision_id not in seen_decisions:
                seen_decisions.add(decision_id)
                pkg.decisions.append({
                    "decision_id": decision_id,
                    "outcome": gov.get("outcome", ""),
                    "permission": gov.get("permission", "")
                })
                pkg.disclosure.include(
                    artifact_id=decision_id,
                    reason="Review model requires full decision context for validation",
                    permission_basis="entity.admin"
                )
            
            prov = r.get("provenance_chain", {})
            pkg.provenance.append({
                "chain_id": prov.get("chain_id", ""),
                "source": prov.get("source_export", {}).get("provider", ""),
                "entries": len(prov.get("entries", []))
            })
            
            # Include artifact count metadata
            pkg.disclosure.include(
                artifact_id=f"receipt:{r.get('receipt_id','')[:16]}",
                reason="Full receipt context required for governance validation",
                permission_basis="entity.admin"
            )
        
        pkg.evidence_refs = [
            f"disclosure:ci-review-{pkg.package_id[:12]}",
            f"receipts:{len(receipts)}",
            f"decisions:{len(seen_decisions)}"
        ]
        self.total_packages_built += 1
        return pkg
