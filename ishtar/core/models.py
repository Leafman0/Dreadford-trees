
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

# ----- Ichor rank helpers -----
ICHOR_RANKS = ["Bloodling", "Neophyte", "Scion", "Elder", "Ascendant", "Ancient Evil"]
_RANK_INDEX = {name.lower(): i for i, name in enumerate(ICHOR_RANKS)}

def rank_to_index(value) -> int:
    if isinstance(value, int):
        return max(0, min(len(ICHOR_RANKS) - 1, value))
    if isinstance(value, str):
        return _RANK_INDEX.get(value.strip().lower(), 0)
    return 0

def rank_name(index_or_name) -> str:
    if isinstance(index_or_name, str):
        return index_or_name if index_or_name in ICHOR_RANKS else ICHOR_RANKS[0]
    i = rank_to_index(index_or_name)
    return ICHOR_RANKS[i]

@dataclass
class SkillNode:
    id: str
    name: str
    cost: int
    description: str = ""
    prereq: List[str] = field(default_factory=list)  # 0 or 1 element
    ichor_rank: int = 0  # required ichor rank (index)

@dataclass
class SkillTree:
    id: str
    name: str
    description: str = ""
    nodes: Dict[str, SkillNode] = field(default_factory=dict)

    @staticmethod
    def from_dict(data: dict) -> "SkillTree":
        nodes = {
            n["id"]: SkillNode(
                id=n["id"],
                name=n.get("name", n["id"]),
                cost=int(n.get("cost", 0)),
                description=n.get("description", ""),
                prereq=list(n.get("prereq", [])),
                ichor_rank=rank_to_index(n.get("ichor_rank", 0)),
            )
            for n in data.get("nodes", [])
        }
        return SkillTree(
            id=data["id"],
            name=data.get("name", data["id"]),
            description=data.get("description", ""),
            nodes=nodes,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": [{
                "id": n.id,
                "name": n.name,
                "cost": n.cost,
                "description": n.description,
                "prereq": n.prereq,
                "ichor_rank": rank_name(n.ichor_rank),
            } for n in self.nodes.values()]
        }

@dataclass
class Character:
    name: str
    xp_pool: int = 0
    trees: List[str] = field(default_factory=list)
    unlocked: Dict[str, Set[str]] = field(default_factory=dict)  # tree_id -> set(node_id)
    image: Optional[str] = None
    ichor_rank: int = 0  # current character ichor rank (index)

    @staticmethod
    def from_dict(d: dict) -> "Character":
        return Character(
            name=d["name"],
            xp_pool=int(d.get("xp_pool", 0)),
            trees=list(d.get("trees", [])),
            unlocked={k: set(v) for k, v in d.get("unlocked", {}).items()},
            image=d.get("image"),
            ichor_rank=rank_to_index(d.get("ichor_rank", 0)),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "xp_pool": self.xp_pool,
            "trees": self.trees,
            "unlocked": {k: sorted(list(v)) for k, v in self.unlocked.items()},
            "image": self.image,
            "ichor_rank": rank_name(self.ichor_rank),
        }

    # ---- XP helpers ----
    def xp_spent_for_tree(self, tree: "SkillTree") -> int:
        ids = self.unlocked.get(tree.id, set())
        return sum(tree.nodes[nid].cost for nid in ids if nid in tree.nodes)

    def xp_spent_total(self, trees_by_id: Dict[str, "SkillTree"]) -> int:
        total = 0
        for tid, ids in self.unlocked.items():
            t = trees_by_id.get(tid)
            if not t:
                continue
            total += sum(t.nodes[n].cost for n in ids if n in t.nodes)
        return total

    # ---- Unlock helpers ----
    def can_unlock(self, tree: "SkillTree", node_id: str, trees_by_id: Dict[str, "SkillTree"]) -> Tuple[bool, str]:
        node = tree.nodes.get(node_id)
        if not node:
            return False, "Node not found."
        if node_id in self.unlocked.get(tree.id, set()):
            return True, "Already unlocked."

        # Ichor rank gate
        if node.ichor_rank > self.ichor_rank:
            return False, f"Ichor Rank {rank_name(node.ichor_rank)} required."

        # Prerequisite gate
        have = self.unlocked.get(tree.id, set())
        missing = [p for p in node.prereq if p not in have]
        if missing:
            return False, f"Requires: {missing[0]}"

        # XP: allowed to go negative (by design), so no block.
        return True, "OK"

    def reasons_for(self, tree: "SkillTree", node_id: str) -> Optional[str]:
        node = tree.nodes.get(node_id)
        if not node:
            return "Node not found."
        if node_id in self.unlocked.get(tree.id, set()):
            return None
        if node.ichor_rank > self.ichor_rank:
            return f"Ichor Rank {rank_name(node.ichor_rank)} required."
        have = self.unlocked.get(tree.id, set())
        missing = [p for p in node.prereq if p not in have]
        if missing:
            return f"Requires: {missing[0]}"
        return None

    def unlock(self, tree: "SkillTree", node_id: str) -> None:
        self.unlocked.setdefault(tree.id, set()).add(node_id)

    def lock(self, tree: "SkillTree", node_id: str) -> None:
        self.unlocked.setdefault(tree.id, set()).discard(node_id)
