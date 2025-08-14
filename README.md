# ISHTAR — Dreadford RPG Skill Tree Tracker & Editor

**ISHTAR** is an intuitive application for tracking and editing trees.  
It supports multiple characters, XP tracking, prerequisites, and *Ichor Rank* gating, with a built-in visual editor for creating and managing skill trees.

---

## ✨ Features

### Core Usability
- **Clickable, vertical skill trees** with automatic layout.
- **XP Tracking** per character and per tree (overspending allowed; negative XP shown in red).
- **Prerequisite Dependencies**: nodes can require other nodes.
- **Ichor Rank Gating**:  
  - Character ranks: Bloodling → Neophyte → Scion → Elder → Ascendant → Ancient Evil.  
  - Nodes require a minimum rank; higher-rank nodes are colored progressively redder.
  - Unlocked powers are green.
- **Markdown descriptions** for skills (headers, lists, emphasis supported).
- **Hover highlighting** of prerequisite & dependent chains.
- **Tooltip requirements** for locked nodes.

### Usability
- **Resizable skill details panel** for long descriptions.
- **Search bar (Ctrl+F)** to jump to skills by name or ID.
- **Legend overlay** for Ichor Rank colors.
- **Planning mode**: freely toggle nodes before committing changes.
- **Ichor gate preview**: dim nodes above current character rank.
- **Per-tree XP summary**.

### Editor Tools
- **Tree creation & editing** with drag-and-drop nodes and dependencies.
- **CSV/TSV bulk import** for spreadsheet workflows.
- **Templates & duplication** for rapid tree building.
- **Undo/Redo** stack for editing safety.

### Quality of Life
- **Font scaling** presets and **High-Contrast** theme.
- **Autosave** every 20s; restores drafts after crashes.
- **Cross-platform** (Windows, macOS, Linux).
- **Buildable to single-file executable** via PyInstaller.

---

## 📦 Installation

### Requirements
- Python 3.9+
- [PySide6](https://pypi.org/project/PySide6/)

Install dependencies:
```bash
pip install -r requirements.txt