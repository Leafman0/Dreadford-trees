
from __future__ import annotations
import sys
from pathlib import Path
from PySide6 import QtWidgets
from ishtar.ui.windows.main import MainWindow, apply_dark_palette
from ishtar.io.storage import Storage

def main():
    root = Path(__file__).resolve().parent
    app = QtWidgets.QApplication(sys.argv)
    apply_dark_palette(app)
    win = MainWindow(Storage(root))
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
