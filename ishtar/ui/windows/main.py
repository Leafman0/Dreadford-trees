from __future__ import annotations
import json
from typing import Dict, Optional, Set
from pathlib import Path
from PySide6 import QtWidgets, QtCore, QtGui
from ...core.models import Character, SkillTree, rank_name
from ...io.storage import Storage
from ..views.canvas import TreeCanvas

def apply_dark_palette(app: QtWidgets.QApplication, high_contrast: bool=False) -> None:
    pal = QtGui.QPalette()
    if not high_contrast:
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor(32, 33, 36))
        pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
        pal.setColor(QtGui.QPalette.Base, QtGui.QColor(24, 25, 27))
        pal.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(41, 42, 45))
        pal.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
        pal.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
        pal.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
        pal.setColor(QtGui.QPalette.Button, QtGui.QColor(41, 42, 45))
        pal.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
        pal.setColor(QtGui.QPalette.Highlight, QtGui.QColor(66, 133, 244))
        pal.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.white)
    else:
        # high contrast variant
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0))
        pal.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
        pal.setColor(QtGui.QPalette.Base, QtGui.QColor(0, 0, 0))
        pal.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(20, 20, 20))
        pal.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
        pal.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
        pal.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
        pal.setColor(QtGui.QPalette.Button, QtGui.QColor(20, 20, 20))
        pal.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
        pal.setColor(QtGui.QPalette.Highlight, QtGui.QColor(255, 255, 0))
        pal.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
    app.setPalette(pal)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage
        self.trees_by_id: Dict[str, SkillTree] = self.storage.load_trees()
        self.current_char: Optional[Character] = None
        self.current_tree: Optional[SkillTree] = None
        self.setWindowTitle("Ishtar")
        self.resize(1280, 860)

        self._planned_mode = False
        self._planned_unlocked: Dict[str, Set[str]] = {}

        self._build_ui()
        self._reload_all()
        self._start_autosave_timer()

    # ---- UI ----
    def _build_ui(self) -> None:
        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)

        top = QtWidgets.QHBoxLayout(); root.addLayout(top, 1)

        # Sidebar
        left = QtWidgets.QVBoxLayout(); top.addLayout(left, 0)
        title = QtWidgets.QLabel("Ishtar"); title.setStyleSheet("font-size:22px; font-weight:800;")
        left.addWidget(title)

        # Character select
        row = QtWidgets.QHBoxLayout(); left.addLayout(row)
        row.addWidget(QtWidgets.QLabel("Character:"))
        self.cmb_char = QtWidgets.QComboBox(); row.addWidget(self.cmb_char, 1)
        self.btn_new_char = QtWidgets.QPushButton("New"); row.addWidget(self.btn_new_char)
        self.btn_save_char = QtWidgets.QPushButton("Save"); row.addWidget(self.btn_save_char)

        # Portrait
        imgrow = QtWidgets.QHBoxLayout(); left.addLayout(imgrow)
        self.lbl_img = QtWidgets.QLabel(); self.lbl_img.setFixedSize(120, 120)
        self.lbl_img.setStyleSheet("background:#2b2c2f; border:1px solid #3a3b3e; border-radius:8px; color:#9AA0A6;")
        self.lbl_img.setAlignment(QtCore.Qt.AlignCenter)
        self.btn_set_img = QtWidgets.QPushButton("Set Image")
        imgrow.addWidget(self.lbl_img); imgrow.addWidget(self.btn_set_img, 1)

        # Ichor rank + XP
        rank_row = QtWidgets.QHBoxLayout(); left.addLayout(rank_row)
        rank_row.addWidget(QtWidgets.QLabel("Ichor Rank:"))
        self.cmb_ichor = QtWidgets.QComboBox()
        self.cmb_ichor.addItems(["Bloodling", "Neophyte", "Scion", "Elder", "Ascendant", "Ancient Evil"])
        rank_row.addWidget(self.cmb_ichor, 1)

        xp = QtWidgets.QHBoxLayout(); left.addLayout(xp)
        xp.addWidget(QtWidgets.QLabel("XP Pool:"))
        self.sp_xp = QtWidgets.QSpinBox(); self.sp_xp.setRange(-1_000_000, 1_000_000); xp.addWidget(self.sp_xp)
        self.lbl_xp = QtWidgets.QLabel("Spent: 0  |  Remaining: 0"); left.addWidget(self.lbl_xp)

        # Planning & gate preview
        self.chk_planning = QtWidgets.QCheckBox("Planning mode")
        self.chk_gate = QtWidgets.QCheckBox("Show only unlockable with current Ichor")
        left.addWidget(self.chk_planning)
        left.addWidget(self.chk_gate)

        left.addWidget(self._hline())

        # Tree chooser
        row2 = QtWidgets.QHBoxLayout(); left.addLayout(row2)
        row2.addWidget(QtWidgets.QLabel("Tree:"))
        self.cmb_tree = QtWidgets.QComboBox(); row2.addWidget(self.cmb_tree, 1)
        self.btn_add_tree = QtWidgets.QPushButton("Add to Character"); row2.addWidget(self.btn_add_tree)

        left.addWidget(QtWidgets.QLabel("Character Trees:"))
        self.lst_trees = QtWidgets.QListWidget(); self.lst_trees.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        left.addWidget(self.lst_trees, 1)

        row3 = QtWidgets.QHBoxLayout(); left.addLayout(row3)
        self.btn_remove_tree = QtWidgets.QPushButton("Remove")
        self.btn_refresh = QtWidgets.QPushButton("Refresh Trees")
        row3.addWidget(self.btn_remove_tree); row3.addWidget(self.btn_refresh)

        # Right side
        right = QtWidgets.QVBoxLayout(); top.addLayout(right, 1)

        # Search + zoom row
        sr = QtWidgets.QHBoxLayout()
        self.search_edit = QtWidgets.QLineEdit(); self.search_edit.setPlaceholderText("Search (Ctrl+F)…")
        self.btn_search_next = QtWidgets.QPushButton("Next")
        self.btn_zoom_out = QtWidgets.QPushButton("−"); self.btn_zoom_in = QtWidgets.QPushButton("+"); self.btn_zoom_reset = QtWidgets.QPushButton("Reset")
        for b in (self.btn_zoom_out, self.btn_zoom_in, self.btn_zoom_reset): b.setFixedWidth(60)
        sr.addWidget(self.search_edit, 1); sr.addWidget(self.btn_search_next)
        sr.addStretch(1); sr.addWidget(self.btn_zoom_out); sr.addWidget(self.btn_zoom_in); sr.addWidget(self.btn_zoom_reset)
        right.addLayout(sr, 0)

        # Splitter: canvas / details
        self.split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.canvas = TreeCanvas(allow_zoom=True)
        self.detail_view = QtWidgets.QTextBrowser()
        f = self.detail_view.font(); f.setPointSize(12); self.detail_view.setFont(f)
        self.detail_view.setOpenExternalLinks(True)
        self.detail_view.setStyleSheet("QTextBrowser { background:#2b2c2f; border:1px solid #3a3b3e; border-radius:8px; padding:10px; }")
        self.split.addWidget(self.canvas); self.split.addWidget(self.detail_view)
        self.split.setStretchFactor(0, 3); self.split.setStretchFactor(1, 2)
        right.addWidget(self.split, 1)

        # Menus
        m = self.menuBar().addMenu("&File")
        self.act_export = m.addAction("Export Character…")
        self.act_import = m.addAction("Import Character…")
        m.addSeparator(); m.addAction("Quit").triggered.connect(self.close)

        tools = self.menuBar().addMenu("&Tools")
        self.act_editor = tools.addAction("Tree Editor / Creator")

        view = self.menuBar().addMenu("&View")
        self.act_font_small = view.addAction("Font: Small")
        self.act_font_default = view.addAction("Font: Default")
        self.act_font_large = view.addAction("Font: Large")
        self.act_high_contrast = view.addAction("High Contrast Theme"); self.act_high_contrast.setCheckable(True)

        self._apply_styles()

        # connections
        self.cmb_char.currentIndexChanged.connect(self._on_select_char)
        self.cmb_tree.currentIndexChanged.connect(lambda _: None)
        self.lst_trees.currentItemChanged.connect(self._on_select_char_tree)
        self.cmb_ichor.currentIndexChanged.connect(self._on_ichor_changed)

        self.btn_new_char.clicked.connect(self._on_new_char)
        self.btn_save_char.clicked.connect(self._on_save_char)
        self.btn_set_img.clicked.connect(self._on_set_image)
        self.sp_xp.valueChanged.connect(self._on_xp_changed)

        self.btn_add_tree.clicked.connect(self._on_add_tree_to_char)
        self.btn_remove_tree.clicked.connect(self._on_remove_tree_from_char)
        self.btn_refresh.clicked.connect(self._on_refresh_trees)

        self.canvas.nodeSelected.connect(self._on_node_selected)
        self.canvas.checkboxToggled.connect(self._on_checkbox_toggled)

        self.btn_zoom_in.clicked.connect(lambda: self._zoom_buttons(+1))
        self.btn_zoom_out.clicked.connect(lambda: self._zoom_buttons(-1))
        self.btn_zoom_reset.clicked.connect(self.canvas.reset_zoom)

        # Search
        self.btn_search_next.clicked.connect(self._on_search_next)
        self.search_edit.returnPressed.connect(self._on_search_next)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self, activated=self._focus_search)

        # Planning & gate preview
        self.chk_planning.toggled.connect(self._on_planning_toggled)
        self.chk_gate.toggled.connect(self._on_gate_toggled)

        # View menu
        self.act_font_small.triggered.connect(lambda: self._set_font_size(10))
        self.act_font_default.triggered.connect(lambda: self._set_font_size(11))
        self.act_font_large.triggered.connect(lambda: self._set_font_size(13))
        self.act_high_contrast.toggled.connect(self._toggle_high_contrast)

        # Export / Import
        self.act_export.triggered.connect(self._on_export_character)
        self.act_import.triggered.connect(self._on_import_character)
        self.act_editor.triggered.connect(self._open_editor)

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', 'Inter', sans-serif; color:#E8EAED; }
            QComboBox, QSpinBox, QPushButton, QListWidget, QPlainTextEdit, QLineEdit, QTableWidget, QGroupBox, QTextBrowser {
                padding: 6px; font-size: 12px; background:#2b2c2f; color:#E8EAED; border:1px solid #3a3b3e; border-radius:8px;
            }
            QPushButton { background:#3a3b3e; border:1px solid #5f6368; border-radius:8px; }
            QPushButton:hover { background:#44474a; }
            QMenuBar { font-size: 12px; background:#202124; color:#E8EAED; }
            QMenu { background:#2b2c2f; color:#E8EAED; }
        """)

    def _hline(self):
        fr = QtWidgets.QFrame(); fr.setFrameShape(QtWidgets.QFrame.HLine); fr.setFrameShadow(QtWidgets.QFrame.Sunken)
        fr.setStyleSheet("color:#5f6368;"); return fr

    # ---- data reload ----
    def _reload_all(self) -> None:
        self.trees_by_id = self.storage.load_trees()
        self.cmb_tree.blockSignals(True); self.cmb_tree.clear()
        for tid, t in sorted(self.trees_by_id.items(), key=lambda kv: kv[1].name.lower()):
            self.cmb_tree.addItem(f"{t.name} ({tid})", tid)
        self.cmb_tree.blockSignals(False)

        self.cmb_char.blockSignals(True); self.cmb_char.clear()
        for name in self.storage.list_characters():
            self.cmb_char.addItem(name, name)
        self.cmb_char.blockSignals(False)
        if self.cmb_char.count(): self.cmb_char.setCurrentIndex(0)
        else: self.current_char = None; self._update_ui()

    def _update_ui(self) -> None:
        if not self.current_char:
            self.sp_xp.setValue(0); self.lst_trees.clear(); self.canvas.clear_all()
            self._set_char_image(None); self._update_xp_labels(); self.detail_view.setMarkdown("")
            return

        self.sp_xp.blockSignals(True); self.sp_xp.setValue(self.current_char.xp_pool); self.sp_xp.blockSignals(False)
        self.cmb_ichor.blockSignals(True); self.cmb_ichor.setCurrentIndex(self.current_char.ichor_rank); self.cmb_ichor.blockSignals(False)

        self.lst_trees.clear()
        for tid in self.current_char.trees:
            t = self.trees_by_id.get(tid); 
            if not t: continue
            spent = self.current_char.xp_spent_for_tree(t)
            n_nodes = len(self.current_char.unlocked.get(tid, set()))
            it = QtWidgets.QListWidgetItem(f"{t.name} ({tid}) — {n_nodes} nodes, {spent} XP")
            it.setData(QtCore.Qt.UserRole, tid)
            self.lst_trees.addItem(it)

        if self.lst_trees.count(): self.lst_trees.setCurrentRow(0)
        self._set_char_image(self.storage.character_image_path(self.current_char))
        self._update_xp_labels()

    def _update_xp_labels(self) -> None:
        if not self.current_char: self.lbl_xp.setText("Spent: 0  |  Remaining: 0"); return
        spent = self.current_char.xp_spent_total(self.trees_by_id); rem = self.current_char.xp_pool - spent
        warn = "  ⚠ overspent" if rem < 0 else ""
        color = "#ff6b6b" if rem < 0 else "#E8EAED"
        self.lbl_xp.setText(f"<span style='color:{color}'>Spent: {spent}  |  Remaining: {rem}{warn}</span>")

    # ---- handlers ----
    def _on_select_char(self):
        name = self.cmb_char.currentData()
        if not name: self.current_char=None; self._update_ui(); return
        self.current_char = self.storage.load_character(name); self._update_ui()

    def _on_select_char_tree(self):
        if not self.current_char: return
        it = self.lst_trees.currentItem()
        if not it: self.canvas.clear_all(); return
        tid = it.data(QtCore.Qt.UserRole)
        self.current_tree = self.trees_by_id.get(tid)
        if self.current_tree:
            unlocked = self._get_unlocked_for_view(tid)
            self.canvas.load_tree(self.current_tree, unlocked)
            self._refresh_block_reasons()
            self.canvas.set_ichor_preview(self.chk_gate.isChecked(), self.current_char.ichor_rank)
            self.detail_view.setMarkdown("**Select a skill to see details.**")

    def _on_new_char(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "New Character", "Enter character name:")
        if not ok or not name.strip(): return
        if name in self.storage.list_characters():
            QtWidgets.QMessageBox.warning(self, "Exists", "Character already exists."); return
        self.current_char = Character(name=name.strip())
        self.storage.save_character(self.current_char); self._reload_all()
        idx = self.cmb_char.findData(self.current_char.name); 
        if idx >= 0: self.cmb_char.setCurrentIndex(idx)

    def _on_save_char(self):
        if not self.current_char: return
        self.storage.save_character(self.current_char)

    def _on_set_image(self):
        if not self.current_char: return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose Image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path: return
        self.storage.set_character_image(self.current_char, Path(path))
        self._set_char_image(self.storage.character_image_path(self.current_char))

    def _set_char_image(self, p: Optional[Path]):
        if not p: self.lbl_img.setPixmap(QtGui.QPixmap()); self.lbl_img.setText("No Image"); return
        pm = QtGui.QPixmap(str(p))
        if pm.isNull(): self.lbl_img.setText("No Image"); return
        self.lbl_img.setText("")
        self.lbl_img.setPixmap(pm.scaled(self.lbl_img.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

    def _on_xp_changed(self, v: int):
        if not self.current_char: return
        self.current_char.xp_pool = int(v); self._update_xp_labels()

    def _on_ichor_changed(self, idx: int):
        if not self.current_char: return
        self.current_char.ichor_rank = idx
        self._refresh_block_reasons()
        self.canvas.set_ichor_preview(self.chk_gate.isChecked(), idx)

    def _on_add_tree_to_char(self):
        if not self.current_char: return
        tid = self.cmb_tree.currentData()
        if not tid: return
        if tid in self.current_char.trees:
            QtWidgets.QMessageBox.information(self, "Info", "Tree already added to character."); return
        self.current_char.trees.append(tid); self.current_char.unlocked.setdefault(tid, set())
        self._update_ui()

    def _on_remove_tree_from_char(self):
        if not self.current_char: return
        it = self.lst_trees.currentItem()
        if not it: return
        tid = it.data(QtCore.Qt.UserRole)
        if QtWidgets.QMessageBox.question(self, "Remove Tree", f"Remove '{tid}' from character?") == QtWidgets.QMessageBox.Yes:
            if tid in self.current_char.trees: self.current_char.trees.remove(tid)
            self._update_ui()

    def _on_refresh_trees(self):
        self.trees_by_id = self.storage.load_trees()
        self.cmb_tree.blockSignals(True); self.cmb_tree.clear()
        for tid, t in sorted(self.trees_by_id.items(), key=lambda kv: kv[1].name.lower()):
            self.cmb_tree.addItem(f"{t.name} ({tid})", tid)
        self.cmb_tree.blockSignals(False)
        self._update_ui()

    def _on_node_selected(self, node_id: str):
        if not (self.current_char and self.current_tree): return
        n = self.current_tree.nodes.get(node_id); 
        if not n: return

        have = self._get_unlocked_for_view(self.current_tree.id)
        has_prereq = (not n.prereq) or (n.prereq[0] in have)
        has_rank = (self.current_char.ichor_rank >= n.ichor_rank)

        md = []
        md.append(f"### {n.name}")
        md.append(f"**Cost:** {n.cost}  |  **Ichor:** {rank_name(n.ichor_rank)}")
        md.append("")
        md.append(("✅" if has_prereq else "❌") + f" **Prerequisite:** " + (n.prereq[0] if n.prereq else "None"))
        md.append(("✅" if has_rank else "❌") + f" **Ichor Rank:** {rank_name(n.ichor_rank)}")
        md.append("")
        md.append(n.description or "_No description._")
        self.detail_view.setMarkdown("\n".join(md))

    def _on_checkbox_toggled(self, node_id: str):
        if not (self.current_char and self.current_tree): return
        tid = self.current_tree.id
        have = self._get_unlocked_for_view(tid)
        if node_id in have:
            # lock
            if self._planned_mode:
                self._planned_unlocked[tid].discard(node_id)
            else:
                self.current_char.lock(self.current_tree, node_id)
            self._post_toggle()
            return
        # unlock (XP allowed negative; can_unlock checks rank/prereq)
        ok, msg = self.current_char.can_unlock(self.current_tree, node_id, self.trees_by_id)
        if not ok and not self._planned_mode:
            QtWidgets.QMessageBox.warning(self, "Cannot Unlock", msg); return
        if self._planned_mode:
            self._planned_unlocked[tid].add(node_id)
        else:
            self.current_char.unlock(self.current_tree, node_id)
        self._post_toggle()

    def _post_toggle(self):
        # reload current tree view state and update labels
        it = self.lst_trees.currentItem()
        if it: self._on_select_char_tree()
        self._update_xp_labels()
        self._refresh_block_reasons()

    # ---- planning & gate preview ----
    def _get_unlocked_for_view(self, tid: str) -> Set[str]:
        base = set(self.current_char.unlocked.get(tid, set()))
        if not self._planned_mode: return base
        plan = self._planned_unlocked.setdefault(tid, set())
        # show base union plan, but not beyond due to missing data; this is a simple preview
        return (base | plan) - (base & set())

    def _on_planning_toggled(self, checked: bool):
        self._planned_mode = checked
        if checked and self.current_tree:
            self._planned_unlocked.setdefault(self.current_tree.id, set())
        self._on_select_char_tree()

    def _on_gate_toggled(self, checked: bool):
        if not self.current_char: return
        self.canvas.set_ichor_preview(checked, self.current_char.ichor_rank)

    # ---- search ----
    def _focus_search(self):
        self.search_edit.setFocus(QtCore.Qt.ShortcutFocusReason); self.search_edit.selectAll()

    def _on_search_next(self):
        q = self.search_edit.text()
        self.canvas.prepare_search(q)
        nid = self.canvas.next_search_hit()
        if nid:
            self._on_node_selected(nid)

    # ---- view tweaks ----
    def _set_font_size(self, pt: int):
        f = self.font(); f.setPointSize(pt); self.setFont(f)

    def _toggle_high_contrast(self, on: bool):
        apply_dark_palette(QtWidgets.QApplication.instance(), high_contrast=on)

    # ---- Export / Import ----
    def _on_export_character(self):
        if not self.current_char: return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Character", f"{self.current_char.name}.zip", "ZIP (*.zip)")
        if not path: return
        if self.storage.export_character_zip(self.current_char.name, Path(path)):
            QtWidgets.QMessageBox.information(self, "Exported", "Character exported.")
        else:
            QtWidgets.QMessageBox.critical(self, "Error", "Export failed.")

    def _on_import_character(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Character", "", "ZIP or JSON (*.zip *.json)")
        if not path: return
        name = self.storage.import_character(Path(path))
        if not name: QtWidgets.QMessageBox.critical(self, "Error", "Import failed."); return
        self._reload_all(); idx = self.cmb_char.findData(name); 
        if idx >= 0: self.cmb_char.setCurrentIndex(idx)
        QtWidgets.QMessageBox.information(self, "Imported", f"Imported character '{name}'.")

    def _open_editor(self):
        from .editor import TreeEditorWindow
        dlg = TreeEditorWindow(self.storage, self.trees_by_id, self); dlg.exec()
        self._on_refresh_trees()

    # ---- helpers ----
    def _refresh_block_reasons(self):
        if not (self.current_char and self.current_tree): return
        reasons: Dict[str, Optional[str]] = {}
        for nid in self.current_tree.nodes.keys():
            reasons[nid] = self.current_char.reasons_for(self.current_tree, nid)
        self.canvas.apply_block_reasons(reasons)

    def _start_autosave_timer(self):
        self._autosave = QtCore.QTimer(self); self._autosave.setInterval(20000)
        self._autosave.timeout.connect(self._autosave_tick); self._autosave.start()

    def _autosave_tick(self):
        if not self.current_char: return
        try:
            data = self.current_char.to_dict()
            # write next to character file
            p = self.storage.chars_dir / f"{self.current_char.name}.autosave.json"
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
