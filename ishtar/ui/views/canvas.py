
from __future__ import annotations
from typing import Dict, List, Optional, Set
from PySide6 import QtWidgets, QtCore, QtGui
from ...core.models import SkillTree
from .colors import ichor_color_locked, COLOR_UNLOCKED
from ..widgets.node_item import NodeItem

NODE_W = 160
NODE_H = 80
LEVEL_V_SPACING = 130
SIBLING_H_SPACING = 40

class TreeCanvas(QtWidgets.QGraphicsView):
    nodeSelected = QtCore.Signal(str)
    checkboxToggled = QtCore.Signal(str)

    def __init__(self, allow_zoom: bool = True):
        super().__init__()
        self._allow_zoom = allow_zoom
        self.setScene(QtWidgets.QGraphicsScene(self))
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.setStyleSheet("background: #202124;")

        self.items_by_id: Dict[str, NodeItem] = {}
        self._edges: List[QtWidgets.QGraphicsPathItem] = []
        self._parents: Dict[str, Optional[str]] = {}
        self._children: Dict[str, List[str]] = {}

        self._zoom = 1.0
        self._search_hits: List[str] = []
        self._search_idx = -1

        # overlay legend toggle
        self.show_legend = True

        # block reasons per node id
        self._block_reasons: Dict[str, Optional[str]] = {}

        # ichor gate preview (dim higher-rank nodes)
        self.ichor_preview_only_unlockable = False
        self.current_char_rank = 0

    # ---- Zoom ----
    def wheelEvent(self, e):  # type: ignore[override]
        if not self._allow_zoom:
            return super().wheelEvent(e)
        factor = 1.15 if e.angleDelta().y() > 0 else 1/1.15
        new_zoom = self._zoom * factor
        if 0.4 <= new_zoom <= 2.2:
            self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
            self.scale(factor, factor)
            self._zoom = new_zoom

    def reset_zoom(self) -> None:
        self.resetTransform(); self._zoom = 1.0

    # ---- Layout helpers ----
    def _build_graph(self, tree: SkillTree):
        self._parents = {nid: (tree.nodes[nid].prereq[0] if tree.nodes[nid].prereq else None) for nid in tree.nodes}
        self._children = {nid: [] for nid in tree.nodes}
        for nid, parent in self._parents.items():
            if parent:
                self._children[parent].append(nid)
        for v in self._children.values():
            v.sort()

    def _roots(self, tree: SkillTree) -> List[str]:
        return sorted([nid for nid, n in tree.nodes.items() if not n.prereq])

    def _layout_positions(self, tree: SkillTree) -> Dict[str, QtCore.QPointF]:
        children = self._children
        roots = self._roots(tree)
        pos: Dict[str, QtCore.QPointF] = {}
        next_x = 0.0
        def layout_sub(nid: str, depth: int) -> float:
            nonlocal next_x
            kids = children.get(nid, [])
            if not kids:
                x = next_x; next_x += NODE_W + SIBLING_H_SPACING
            else:
                xs = [layout_sub(k, depth+1) for k in kids]
                x = sum(xs)/len(xs)
            y = depth * (NODE_H + LEVEL_V_SPACING)
            pos[nid] = QtCore.QPointF(x, y)
            return x
        for r in roots:
            layout_sub(r, 0)
            next_x += NODE_W
        if pos:
            min_x = min(p.x() for p in pos.values())
            for k in pos:
                pos[k].setX(pos[k].x() - min_x + 20)
        return pos

    # ---- Build ----
    def clear_all(self):
        self.scene().clear()
        self.items_by_id.clear(); self._edges.clear()
        self._search_hits = []; self._search_idx = -1
        self._block_reasons.clear()
        self.reset_zoom()

    def load_tree(self, tree: SkillTree, unlocked: Set[str]):
        self.clear_all()
        self._build_graph(tree)
        pos = self._layout_positions(tree)

        # nodes
        for nid, n in tree.nodes.items():
            item = NodeItem(n, unlocked=(nid in unlocked))
            item.setPos(pos.get(nid, QtCore.QPointF(0, 0)))
            item.selected.connect(self.nodeSelected)
            item.checkboxToggled.connect(self.checkboxToggled)
            item.hoverEntered.connect(self._on_hover_entered)
            item.hoverLeft.connect(self._on_hover_left)
            self.scene().addItem(item)
            self.items_by_id[nid] = item

        # edges
        for nid, n in tree.nodes.items():
            if n.prereq:
                parent = n.prereq[0]
                if parent in self.items_by_id:
                    self._add_edge(self.items_by_id[parent].pos(), self.items_by_id[nid].pos())

        self.scene().setSceneRect(self.scene().itemsBoundingRect().adjusted(-40, -40, 80, 80))

    def _add_edge(self, p_parent, p_child) -> None:
        parent_bottom = QtCore.QPointF(p_parent.x()+NODE_W/2, p_parent.y()+NODE_H)
        child_top = QtCore.QPointF(p_child.x()+NODE_W/2, p_child.y())
        mid_y = (parent_bottom.y() + child_top.y())/2
        path = QtGui.QPainterPath(parent_bottom)
        path.lineTo(parent_bottom.x(), mid_y)
        path.lineTo(child_top.x(), mid_y)
        path.lineTo(child_top)
        item = QtWidgets.QGraphicsPathItem(path)
        pen = QtGui.QPen(QtGui.QColor("#5F6368"), 2)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        item.setPen(pen)
        self.scene().addItem(item); self._edges.append(item)

    # ---- Hover highlighting ----
    def _collect_chain(self, nid: str) -> Set[str]:
        seen: Set[str] = set()
        # upward
        cur = nid
        while True:
            p = self._parents.get(cur)
            if not p: break
            seen.add(p); cur = p
        # downward
        stack = [nid]
        while stack:
            u = stack.pop()
            for c in self._children.get(u, []):
                if c not in seen:
                    seen.add(c); stack.append(c)
        seen.add(nid)
        return seen

    def _on_hover_entered(self, nid: str):
        highlight = self._collect_chain(nid)
        for k, item in self.items_by_id.items():
            item.setOpacity(1.0 if k in highlight else 0.25)

    def _on_hover_left(self):
        for item in self.items_by_id.values():
            item.setOpacity(1.0)

    # ---- Search ----
    def prepare_search(self, query: str):
        q = query.strip().lower()
        self._search_hits = [nid for nid, it in self.items_by_id.items()
                             if q and (q in it.node.id.lower() or q in it.node.name.lower())]
        self._search_idx = -1

    def next_search_hit(self) -> Optional[str]:
        if not self._search_hits: return None
        self._search_idx = (self._search_idx + 1) % len(self._search_hits)
        nid = self._search_hits[self._search_idx]
        self.center_on_node(nid)
        return nid

    def center_on_node(self, nid: str):
        it = self.items_by_id.get(nid); 
        if not it: return
        rect = it.mapToScene(it.boundingRect()).boundingRect()
        self.fitInView(rect.adjusted(-80, -60, 80, 60), QtCore.Qt.KeepAspectRatio)

    # ---- Legend ----
    def drawForeground(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:  # type: ignore[override]
        if not self.show_legend: return
        painter.save()
        view_rect = self.viewport().rect()
        margin = 10
        w = 260; h = 52
        x = view_rect.right() - w - margin
        y = view_rect.top() + margin
        # background
        painter.setPen(QtGui.QPen(QtGui.QColor("#5f6368")))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(32, 33, 36, 230)))
        painter.drawRoundedRect(QtCore.QRectF(x, y, w, h), 10, 10)
        # swatches
        labels = ["Bloodling", "Neophyte", "Scion", "Elder", "Ascendant", "Ancient Evil"]
        for i, name in enumerate(labels):
            color = ichor_color_locked(i)
            sw = QtCore.QRectF(x+10+i*36, y+8, 24, 12)
            painter.fillRect(sw, color)
        painter.setPen(QtGui.QPen(QtGui.QColor("#E8EAED")))
        painter.drawText(QtCore.QRectF(x+10, y+26, w-20, 20), QtCore.Qt.AlignLeft, "Unlocked = Green")
        painter.restore()

    # ---- Block reasons from main window ----
    def apply_block_reasons(self, reasons: Dict[str, Optional[str]]):
        self._block_reasons = reasons or {}
        for nid, item in self.items_by_id.items():
            item.set_block_reason(self._block_reasons.get(nid))

    # ---- Ichor gate preview ----
    def set_ichor_preview(self, enabled: bool, char_rank: int):
        self.ichor_preview_only_unlockable = enabled
        self.current_char_rank = char_rank
        if not self.items_by_id: return
        for nid, item in self.items_by_id.items():
            n = item.node
            should_dim = enabled and (n.ichor_rank > char_rank) and not item.unlocked
            item.setOpacity(0.35 if should_dim else 1.0)
