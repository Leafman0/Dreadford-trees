
from __future__ import annotations
from PySide6 import QtWidgets, QtCore, QtGui
from ..views.colors import ichor_color_locked, COLOR_UNLOCKED

NODE_W = 160
NODE_H = 80
NODE_RADIUS = 14

class NodeItem(QtWidgets.QGraphicsObject):
    selected = QtCore.Signal(str)
    checkboxToggled = QtCore.Signal(str)
    hoverEntered = QtCore.Signal(str)
    hoverLeft = QtCore.Signal()

    def __init__(self, node, unlocked: bool = False):
        super().__init__()
        self.node = node
        self.unlocked = unlocked
        self.block_reason: str | None = None
        self._rect = QtCore.QRectF(0, 0, NODE_W, NODE_H)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

        # Title text
        self.text_item = QtWidgets.QGraphicsTextItem(self)
        self.text_item.setDefaultTextColor(QtGui.QColor("#E8EAED"))
        self.text_item.setTextWidth(NODE_W - 20)
        f = self.text_item.font(); f.setPointSizeF(10); f.setBold(True)
        self.text_item.setFont(f)
        self.text_item.setPos(10, 28)  # a bit lower to avoid overlap with checkbox/cost
        doc = self.text_item.document()
        opt = QtGui.QTextOption(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        doc.setDefaultTextOption(opt)
        self.text_item.setPlainText(self.node.name)

        # Tooltip
        self.setToolTip(f"{self.node.name}\nCost: {self.node.cost}\nIchor: {self.node.ichor_rank}\n\n{self.node.description}")

    # --- API ---
    def set_unlocked(self, v: bool):
        self.unlocked = v; self.update()

    def set_block_reason(self, reason: str | None):
        self.block_reason = reason; self.update()

    # --- painting helpers ---
    def boundingRect(self) -> QtCore.QRectF:  # type: ignore[override]
        return self._rect.adjusted(-1, -1, 1, 1)

    def _checkbox_rect(self) -> QtCore.QRectF:
        r = self._rect; s = 16
        return QtCore.QRectF(r.right()-s-8, r.top()+8, s, s)

    # --- paint ---
    def paint(self, p: QtGui.QPainter, opt, widget=None):  # type: ignore[override]
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)

        # Colors
        if self.unlocked:
            brush = QtGui.QBrush(COLOR_UNLOCKED)
            pen = QtGui.QPen(QtGui.QColor("#81C995"), 2)
        else:
            col = ichor_color_locked(self.node.ichor_rank)
            brush = QtGui.QBrush(col)
            pen = QtGui.QPen(QtGui.QColor("#9AA0A6"), 2)

        # Base rounded rect
        path = QtGui.QPainterPath()
        path.addRoundedRect(self._rect, NODE_RADIUS, NODE_RADIUS)
        p.setPen(pen); p.setBrush(brush); p.drawPath(path)

        # Checkbox and XP label
        cb = self._checkbox_rect()
        # greyed checkbox if blocked and not unlocked
        cb_pen = QtGui.QPen(QtGui.QColor("#9AA0A6" if not self.block_reason else "#6b6b6b"), 1)
        p.setPen(cb_pen); p.setBrush(QtGui.QBrush(QtGui.QColor("#202124")))
        p.drawRoundedRect(cb, 3, 3)

        # checkmark
        if self.unlocked:
            cpen = QtGui.QPen(QtGui.QColor("#81C995"), 2)
            p.setPen(cpen)
            mark = QtGui.QPainterPath()
            mark.moveTo(cb.left()+3, cb.center().y())
            mark.lineTo(cb.center().x()-1, cb.bottom()-3)
            mark.lineTo(cb.right()-3, cb.top()+3)
            p.drawPath(mark)

        # XP label with buffer
        p.setPen(QtGui.QPen(QtGui.QColor("#E8EAED")))
        font = p.font(); font.setPointSizeF(9); font.setBold(False)
        p.setFont(font)
        label = f"XP Cost: {self.node.cost}"
        text_rect = QtCore.QRectF(cb.left()-110, cb.top()-8, 106, cb.height()+2)
        p.drawText(text_rect, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, label)

    # --- interaction ---
    def mousePressEvent(self, e):  # type: ignore[override]
        if e.button() == QtCore.Qt.LeftButton:
            # clicking checkbox area toggles if not blocked, otherwise tooltip
            if self._checkbox_rect().contains(e.pos()):
                if self.block_reason and not self.unlocked:
                    QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), self.block_reason)
                    e.accept(); return
                self.checkboxToggled.emit(self.node.id); e.accept(); return
            self.selected.emit(self.node.id); e.accept(); return
        super().mousePressEvent(e)

    def hoverEnterEvent(self, e):  # type: ignore[override]
        self.hoverEntered.emit(self.node.id); super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):  # type: ignore[override]
        self.hoverLeft.emit(); super().hoverLeaveEvent(e)
