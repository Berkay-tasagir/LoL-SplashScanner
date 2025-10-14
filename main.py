import sys
from PyQt5 import QtWidgets
from overlay_window import OverlayWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    w = OverlayWindow()
    w.show()
    sys.exit(app.exec_())
