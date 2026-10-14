"""Software-only Bitcoin mining chain for Brain.

This module creates an unbounded logical worker topology over resources that are
actually available to the host. Logical nodes do not create CPU, energy, or
network capacity. No simulated work is counted as BTC revenue.

The chain is intentionally fail-closed:
- virtual/simulated hashing is evidence of software readiness only;
- real mining requires an authorized execution worker and real network/pool
  evidence;
- BTC revenue requires an observed on-chain or trusted payout record.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SoftwareMiningNode:
    node_id: str
    parent_id: str | None
    role: str = "sha256-worker"
    execution_backend: str = "logical"
    real_hashing_enabled: bool = False


@dataclass
class SoftwareMiningChain:
    chain_id: str = "brain-bitcoin-software-chain"
    nodes: list[SoftwareMiningNode] = field(default_factory=list)

    def append(self, node_id: str) -> SoftwareMiningNode:
        if not node_id.strip():
            raise ValueError("node_id is required")
        if any(node.node_id == node_id for node in self.nodes):
            raise ValueError("duplicate node_id")
        parent = self.nodes[-1].node_id if self.nodes else None
        node = SoftwareMiningNode(node_id=node_id, parent_id=parent)
        self.nodes.append(node)
        return node

    def snapshot(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "logical_node_count": len(self.nodes),
            "nodes": [
                {
                    "node_id": n.node_id,
                    "parent_id": n.parent_id,
                    "role": n.role,
                    "execution_backend": n.execution_backend,
                    "real_hashing_enabled": n.real_hashing_enabled,
                }
                for n in self.nodes
            ],
            "physical_hardware_required": False,
            "unbounded_logical_topology": True,
            "extra_compute_created_by_nodes": False,
            "simulated_revenue_btc": 0.0,
            "verified_revenue_btc": 0.0,
        }

    def revenue_gate(
        self,
        *,
        real_pool_evidence: bool = False,
        payout_evidence: bool = False,
    ) -> dict[str, Any]:
        if not real_pool_evidence:
            return {
                "status": "BLOCKED_NO_REAL_POOL_EVIDENCE",
                "revenue_realized": False,
                "reason": "logical_nodes_or_simulation_are_not_mining_revenue",
            }
        if not payout_evidence:
            return {
                "status": "BLOCKED_NO_BTC_PAYOUT_EVIDENCE",
                "revenue_realized": False,
                "reason": "pool_connection_alone_does_not_prove_received_BTC",
            }
        return {
            "status": "REVENUE_EVIDENCE_ACCEPTED",
            "revenue_realized": True,
            "reason": "real_pool_and_payout_evidence_present",
        }
