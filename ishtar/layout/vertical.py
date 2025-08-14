
from __future__ import annotations
from typing import Dict, List
from PySide6 import QtCore
from ..core.models import SkillTree

NODE_W = 160
NODE_H = 72
LEVEL_V_SPACING = 130
SIBLING_H_SPACING = 40

def compute_positions(tree: SkillTree) -> Dict[str, QtCore.QPointF]:
    children: Dict[str, List[str]] = {nid: [] for nid in tree.nodes}
    for n in tree.nodes.values():
        if n.prereq:
            p = n.prereq[0]
            if p in children: children[p].append(n.id)
    for k in children: children[k].sort()
    roots = sorted([nid for nid, n in tree.nodes.items() if not n.prereq])
    pos: Dict[str, QtCore.QPointF] = {}
    next_x = 0.0
    def layout(nid: str, depth: int) -> float:
        nonlocal next_x
        kids = children.get(nid, [])
        if not kids:
            x = next_x; next_x += NODE_W + SIBLING_H_SPACING
        else:
            xs = [layout(k, depth+1) for k in kids]
            x = sum(xs)/len(xs)
        y = depth*(NODE_H+LEVEL_V_SPACING)
        pos[nid] = QtCore.QPointF(x, y)
        return x
    for r in roots:
        layout(r, 0); next_x += NODE_W
    if pos:
        minx = min(p.x() for p in pos.values())
        for k in pos: pos[k].setX(pos[k].x()-minx+20)
    return pos
