
from __future__ import annotations
from typing import Dict, Optional, List, Tuple
from PySide6 import QtWidgets, QtCore
from ...core.models import SkillTree, SkillNode, rank_to_index, rank_name
from ...core.validation import validate_tree
from ...io.storage import Storage
from ..views.canvas import TreeCanvas

class NodeEditorDialog(QtWidgets.QDialog):
    def __init__(self, parent, node_ids: List[str], node: Optional[SkillNode] = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Node" if node else "Add Node")
        self.resize(420, 360)
        self.node = node

        form = QtWidgets.QFormLayout(self)
        self.ed_id = QtWidgets.QLineEdit()
        self.ed_name = QtWidgets.QLineEdit()
        self.sp_cost = QtWidgets.QSpinBox(); self.sp_cost.setRange(0, 1_000_000)
        self.ed_desc = QtWidgets.QPlainTextEdit(); self.ed_desc.setMinimumHeight(100)
        self.dd_prereq = QtWidgets.QComboBox(); self.dd_prereq.addItem("(None)", "")
        self.dd_rank = QtWidgets.QComboBox(); self.dd_rank.addItems(["Bloodling","Neophyte","Scion","Elder","Ascendant","Ancient Evil"])

        for nid in node_ids:
            if node and nid == node.id: continue
            self.dd_prereq.addItem(nid, nid)

        if node:
            self.ed_id.setText(node.id); self.ed_id.setEnabled(False)
            self.ed_name.setText(node.name); self.sp_cost.setValue(node.cost)
            self.ed_desc.setPlainText(node.description)
            current = node.prereq[0] if node.prereq else ""
            self.dd_prereq.setCurrentIndex(max(0, self.dd_prereq.findData(current)))
            self.dd_rank.setCurrentIndex(node.ichor_rank)

        form.addRow("ID", self.ed_id)
        form.addRow("Name", self.ed_name)
        form.addRow("Cost", self.sp_cost)
        form.addRow("Description", self.ed_desc)
        form.addRow("Prerequisite", self.dd_prereq)
        form.addRow("Ichor Rank", self.dd_rank)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def result_node(self) -> Optional[SkillNode]:
        nid = self.ed_id.text().strip()
        if not nid: return None
        name = self.ed_name.text().strip() or nid
        cost = int(self.sp_cost.value())
        desc = self.ed_desc.toPlainText().strip()
        pre = self.dd_prereq.currentData() or ""
        prereq = [pre] if pre else []
        ichor_rank = self.dd_rank.currentIndex()
        return SkillNode(id=nid, name=name, cost=cost, description=desc, prereq=prereq, ichor_rank=ichor_rank)

class TreeEditorWindow(QtWidgets.QDialog):
    def __init__(self, storage: Storage, trees_by_id: Dict[str, SkillTree], parent=None):
        super().__init__(parent)
        self.storage = storage
        self.trees_by_id = trees_by_id
        self.setWindowTitle("Tree Editor / Creator")
        self.resize(1100, 680)

        self._undo: List[dict] = []
        self._redo: List[dict] = []

        main = QtWidgets.QHBoxLayout(self)

        # left: list + metadata
        left = QtWidgets.QVBoxLayout(); main.addLayout(left, 0)
        self.tree_list = QtWidgets.QListWidget()
        for tid, t in sorted(self.trees_by_id.items(), key=lambda kv: kv[1].name.lower()):
            it = QtWidgets.QListWidgetItem(f"{t.name} ({t.id})"); it.setData(QtCore.Qt.UserRole, t.id)
            self.tree_list.addItem(it)
        left.addWidget(QtWidgets.QLabel("Trees:")); left.addWidget(self.tree_list, 1)

        meta = QtWidgets.QFormLayout(); left.addLayout(meta)
        self.ed_tree_id = QtWidgets.QLineEdit()
        self.ed_tree_name = QtWidgets.QLineEdit()
        self.ed_tree_desc = QtWidgets.QPlainTextEdit(); self.ed_tree_desc.setMinimumHeight(80)
        meta.addRow("Tree ID", self.ed_tree_id)
        meta.addRow("Tree Name", self.ed_tree_name)
        meta.addRow("Description", self.ed_tree_desc)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_new_tree = QtWidgets.QPushButton("New")
        self.btn_new_from_template = QtWidgets.QPushButton("New from Template")
        self.btn_dup_tree = QtWidgets.QPushButton("Duplicate")
        self.btn_delete_tree = QtWidgets.QPushButton("Delete File")
        self.btn_save_tree = QtWidgets.QPushButton("Save")
        btn_row.addWidget(self.btn_new_tree); btn_row.addWidget(self.btn_new_from_template); btn_row.addWidget(self.btn_dup_tree)
        btn_row.addWidget(self.btn_delete_tree); btn_row.addWidget(self.btn_save_tree)
        left.addLayout(btn_row)

        # right: table + preview
        right = QtWidgets.QVBoxLayout(); main.addLayout(right, 1)
        self.tbl = QtWidgets.QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["ID", "Name", "Cost", "Prereq", "Ichor"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        right.addWidget(self.tbl, 1)

        rowbtns = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Node")
        self.btn_edit = QtWidgets.QPushButton("Edit Node")
        self.btn_remove = QtWidgets.QPushButton("Remove Node")
        self.btn_import = QtWidgets.QPushButton("Import CSV/TSV")
        self.btn_undo = QtWidgets.QPushButton("Undo")
        self.btn_redo = QtWidgets.QPushButton("Redo")
        rowbtns.addWidget(self.btn_add); rowbtns.addWidget(self.btn_edit); rowbtns.addWidget(self.btn_remove)
        rowbtns.addStretch(1); rowbtns.addWidget(self.btn_import); rowbtns.addWidget(self.btn_undo); rowbtns.addWidget(self.btn_redo)
        right.addLayout(rowbtns)

        self.preview = TreeCanvas(allow_zoom=True)
        right.addWidget(self.preview, 2)

        # connections
        self.tree_list.currentItemChanged.connect(self._on_select_tree)
        self.btn_new_tree.clicked.connect(self._on_new_tree)
        self.btn_new_from_template.clicked.connect(self._on_new_from_template)
        self.btn_dup_tree.clicked.connect(self._on_duplicate_tree)
        self.btn_delete_tree.clicked.connect(self._on_delete_tree)
        self.btn_save_tree.clicked.connect(self._on_save_tree)
        self.btn_add.clicked.connect(self._on_add_node)
        self.btn_edit.clicked.connect(self._on_edit_node)
        self.btn_remove.clicked.connect(self._on_remove_node)
        self.btn_import.clicked.connect(self._on_import)
        self.btn_undo.clicked.connect(self._on_undo)
        self.btn_redo.clicked.connect(self._on_redo)

        if self.tree_list.count(): self.tree_list.setCurrentRow(0)

    # ---- helpers ----
    def _get_tree(self) -> Optional[SkillTree]:
        it = self.tree_list.currentItem()
        tid = it.data(QtCore.Qt.UserRole) if it else None
        return self.trees_by_id.get(tid) if tid else None

    def _populate(self, tree: Optional[SkillTree]) -> None:
        if not tree:
            self.ed_tree_id.setText(""); self.ed_tree_name.setText(""); self.ed_tree_desc.setPlainText("")
            self.tbl.setRowCount(0); self.preview.clear_all(); return
        self.ed_tree_id.setText(tree.id); self.ed_tree_name.setText(tree.name); self.ed_tree_desc.setPlainText(tree.description or "")
        self._populate_table(tree); self.preview.load_tree(tree, set())

    def _populate_table(self, tree: SkillTree) -> None:
        nodes = list(tree.nodes.values())
        self.tbl.setRowCount(len(nodes))
        for r, n in enumerate(nodes):
            vals = [n.id, n.name, str(n.cost), ",".join(n.prereq[:1]), rank_name(n.ichor_rank)]
            for c, val in enumerate(vals):
                it = QtWidgets.QTableWidgetItem(val)
                if c == 0: it.setFlags(it.flags() ^ QtCore.Qt.ItemIsEditable)
                self.tbl.setItem(r, c, it)

    # ---- actions ----
    def _on_select_tree(self):
        self._populate(self._get_tree())

    def _on_new_tree(self):
        t = SkillTree(id="new_tree", name="New Tree", description="", nodes={})
        base = t.id; idx = 1
        while t.id in self.trees_by_id: t.id = f"{base}_{idx}"; idx += 1
        self.trees_by_id[t.id] = t
        it = QtWidgets.QListWidgetItem(f"{t.name} ({t.id})"); it.setData(QtCore.Qt.UserRole, t.id)
        self.tree_list.addItem(it); self.tree_list.setCurrentItem(it)
        self._snapshot()

    def _on_new_from_template(self):
        t = SkillTree(id="template_tree", name="Template Tree", description="Starter template", nodes={})
        # simple 3-step chain on two lanes
        t.nodes["root_a"] = SkillNode("root_a","Root A",2,"",[],0)
        t.nodes["a2"] = SkillNode("a2","A2",3,"",["root_a"],1)
        t.nodes["a3"] = SkillNode("a3","A3",4,"",["a2"],2)
        t.nodes["root_b"] = SkillNode("root_b","Root B",2,"",[],0)
        t.nodes["b2"] = SkillNode("b2","B2",3,"",["root_b"],1)
        self.trees_by_id[t.id] = t
        it = QtWidgets.QListWidgetItem(f"{t.name} ({t.id})"); it.setData(QtCore.Qt.UserRole, t.id)
        self.tree_list.addItem(it); self.tree_list.setCurrentItem(it)
        self._snapshot()

    def _on_duplicate_tree(self):
        src = self._get_tree()
        if not src: return
        d = src.to_dict()
        t = SkillTree.from_dict(d)
        base = f"{t.id}_copy"; i = 1
        while f"{base}_{i}" in self.trees_by_id: i += 1
        t.id = f"{base}_{i}"; t.name = f"{t.name} (Copy)"
        self.trees_by_id[t.id] = t
        it = QtWidgets.QListWidgetItem(f"{t.name} ({t.id})"); it.setData(QtCore.Qt.UserRole, t.id)
        self.tree_list.addItem(it); self.tree_list.setCurrentItem(it)
        self._snapshot()

    def _on_delete_tree(self):
        t = self._get_tree()
        if not t: return
        if QtWidgets.QMessageBox.question(self, "Delete", f"Delete tree '{t.id}.json'?") != QtWidgets.QMessageBox.Yes: return
        p = self.storage.trees_dir / f"{t.id}.json"
        if p.exists(): p.unlink()
        self.trees_by_id.pop(t.id, None)
        self.tree_list.takeItem(self.tree_list.currentRow())
        self._populate(None)
        self._snapshot()

    def _on_save_tree(self):
        t = self._get_tree()
        if not t: return
        t.id = self.ed_tree_id.text().strip() or t.id
        t.name = self.ed_tree_name.text().strip() or t.id
        t.description = self.ed_tree_desc.toPlainText().strip()
        ok, errs = validate_tree(t)
        if not ok:
            QtWidgets.QMessageBox.critical(self, "Validation failed", "\n".join(errs)); return
        self.storage.save_tree(t)
        it = self.tree_list.currentItem()
        if it: it.setText(f"{t.name} ({t.id})"); it.setData(QtCore.Qt.UserRole, t.id)
        QtWidgets.QMessageBox.information(self, "Saved", "Tree saved.")

    def _on_add_node(self):
        t = self._get_tree()
        if not t: return
        dlg = NodeEditorDialog(self, list(t.nodes.keys()))
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            n = dlg.result_node(); 
            if not n: return
            if n.id in t.nodes:
                QtWidgets.QMessageBox.warning(self, "Exists", "Node id already exists."); return
            t.nodes[n.id] = n; self._populate_table(t); self.preview.load_tree(t, set()); self._snapshot()

    def _on_edit_node(self):
        t = self._get_tree()
        if not t: return
        row = self.tbl.currentRow()
        if row < 0: return
        nid = self.tbl.item(row, 0).text()
        dlg = NodeEditorDialog(self, list(t.nodes.keys()), node=t.nodes.get(nid))
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            n = dlg.result_node(); 
            if not n: return
            t.nodes[n.id] = n; self._populate_table(t); self.preview.load_tree(t, set()); self._snapshot()

    def _on_remove_node(self):
        t = self._get_tree()
        if not t: return
        row = self.tbl.currentRow()
        if row < 0: return
        nid = self.tbl.item(row, 0).text()
        if QtWidgets.QMessageBox.question(self, "Remove", f"Remove node '{nid}'?") != QtWidgets.QMessageBox.Yes: return
        t.nodes.pop(nid, None)
        for v in t.nodes.values():
            if nid in v.prereq: v.prereq.remove(nid)
        self._populate_table(t); self.preview.load_tree(t, set()); self._snapshot()

    def _on_import(self):
        t = self._get_tree()
        if not t: return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import CSV/TSV", "", "CSV/TSV (*.csv *.tsv *.txt)")
        if not path: return
        # detect delimiter
        with open(path, "r", encoding="utf-8") as f:
            lines = [l.strip("\n") for l in f.readlines() if l.strip()]
        if not lines: return
        sample = lines[0]
        delim = ","
        if "\t" in sample: delim = "\t"
        elif ";" in sample: delim = ";"
        # parse
        for line in lines[1:] if any(h in sample.lower() for h in ["id","name","cost"]) else lines:
            parts = line.split(delim)
            if len(parts) < 3: continue
            idv = parts[0].strip(); name = parts[1].strip() or idv
            cost = int(parts[2].strip() or "0")
            prereq = [parts[3].strip()] if len(parts) > 3 and parts[3].strip() else []
            ichor = rank_to_index(parts[4].strip()) if len(parts) > 4 else 0
            desc = parts[5].strip() if len(parts) > 5 else ""
            t.nodes[idv] = SkillNode(id=idv, name=name, cost=cost, description=desc, prereq=prereq, ichor_rank=ichor)
        self._populate_table(t); self.preview.load_tree(t, set()); self._snapshot()

    # ---- undo/redo ----
    def _snapshot(self):
        t = self._get_tree(); 
        if not t: return
        self._undo.append(t.to_dict()); self._redo.clear()

    def _restore(self, data: dict):
        t = self._get_tree(); 
        if not t: return
        tid = t.id
        new_t = SkillTree.from_dict(data)
        self.trees_by_id[tid] = new_t
        self._populate(new_t)

    def _on_undo(self):
        if not self._undo: return
        cur = self._undo.pop()
        self._redo.append(self._get_tree().to_dict())
        self._restore(cur)

    def _on_redo(self):
        if not self._redo: return
        cur = self._redo.pop()
        self._undo.append(self._get_tree().to_dict())
        self._restore(cur)
