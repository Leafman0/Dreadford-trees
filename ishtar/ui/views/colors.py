
from __future__ import annotations
from PySide6 import QtGui

# Unlocked node green
COLOR_UNLOCKED = QtGui.QColor("#245C2E")

# Gray->red palette for locked nodes (index 0..5)
_PALETTE = ["#3C4043", "#5a3a3a", "#6e2e2e", "#8c2525", "#a81c1c", "#c11212"]

def ichor_color_locked(rank_idx: int) -> QtGui.QColor:
    i = max(0, min(rank_idx, len(_PALETTE)-1))
    return QtGui.QColor(_PALETTE[i])
