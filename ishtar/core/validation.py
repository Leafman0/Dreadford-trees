
from __future__ import annotations
from typing import List, Tuple
from .models import SkillTree, ICHOR_RANKS

def validate_tree(tree: SkillTree) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    ids = set(tree.nodes.keys())
    if not tree.id.strip(): errs.append("Tree ID is required.")
    if not tree.name.strip(): errs.append("Tree name is required.")
    for n in tree.nodes.values():
        if len(n.prereq) > 1:
            errs.append(f"Node '{n.id}' has more than one prerequisite.")
        for p in n.prereq:
            if p not in ids: errs.append(f"Node '{n.id}' has missing prerequisite '{p}'.")
        if n.prereq and n.prereq[0] == n.id:
            errs.append(f"Node '{n.id}' cannot depend on itself.")
        if not (0 <= n.ichor_rank < len(ICHOR_RANKS)):
            errs.append(f"Node '{n.id}' has invalid ichor rank.")
    # cycle check
    state = {}; path: List[str] = []
    graph = {nid: node.prereq[:1] for nid, node in tree.nodes.items()}
    def dfs(u: str) -> bool:
        state[u] = 1
        for v in graph.get(u, []):
            s = state.get(v, 0)
            if s == 0:
                if dfs(v): path.append(v); return True
            elif s == 1:
                path.append(v); return True
        state[u] = 2; return False
    for u in graph:
        if state.get(u,0)==0 and dfs(u):
            errs.append("Cycle detected."); break
    return (len(errs)==0), errs
