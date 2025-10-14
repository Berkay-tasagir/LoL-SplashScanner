from PyQt5 import QtWidgets, QtCore

class ModeSwitch(QtWidgets.QWidget):
    """Sağ altta: 'Düzenle' ve 'Kullan' kutuları yan yana; seçilen gri."""
    modeChanged = QtCore.pyqtSignal(bool)  # True = edit, False = use

    def __init__(self):
        super().__init__()
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self.btn_edit = QtWidgets.QPushButton("Düzenle")
        self.btn_use  = QtWidgets.QPushButton("Kullan")

        for b in (self.btn_edit, self.btn_use):
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.setFixedSize(120, 50)
            b.setStyleSheet("""
                QPushButton {
                    background:#1e1e1e; color:white; font-weight:600; border-radius:8px;
                }
                QPushButton:checked { background:#3a3a3a; }
            """)
            lay.addWidget(b)

        self.btn_edit.setChecked(True)
        # bağlantılar
        self.btn_edit.clicked.connect(lambda: self.modeChanged.emit(True))
        self.btn_use.clicked.connect(lambda: self.modeChanged.emit(False))


class ScanWithSide(QtWidgets.QWidget):
    """Sol altta: Tara + hemen yanında küçük yan menü 'Üstü tara' / 'Altı tara'."""
    sideChosen = QtCore.pyqtSignal(str)  # "top" / "bottom"

    def __init__(self):
        super().__init__()
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.btn_scan = QtWidgets.QPushButton("Tara")
        self.btn_scan.setFixedSize(110, 50)
        self.btn_scan.setStyleSheet("""
            QPushButton { background:#1e1e1e; color:white; font-weight:700; border-radius:8px; }
            QPushButton:hover { background:#2b2b2b; }
        """)
        row.addWidget(self.btn_scan)

        self.side_panel = QtWidgets.QWidget()
        side_lay = QtWidgets.QHBoxLayout(self.side_panel)
        side_lay.setContentsMargins(0, 0, 0, 0)
        side_lay.setSpacing(6)

        self.btn_top = QtWidgets.QPushButton("Üstü tara")
        self.btn_bot = QtWidgets.QPushButton("Altı tara")
        for b in (self.btn_top, self.btn_bot):
            b.setFixedHeight(36)
            b.setStyleSheet("""
                QPushButton { background:#222; color:white; border-radius:6px; padding: 6px 10px; }
                QPushButton:hover { background:#333; }
            """)
            side_lay.addWidget(b)

        self.side_panel.setVisible(False)
        row.addWidget(self.side_panel)

        self.btn_scan.clicked.connect(self._toggle_side_panel)
        self.btn_top.clicked.connect(lambda: self._choose("top"))
        self.btn_bot.clicked.connect(lambda: self._choose("bottom"))

    def _toggle_side_panel(self):
        self.side_panel.setVisible(not self.side_panel.isVisible())

    def _choose(self, side):
        self.side_panel.setVisible(False)
        self.sideChosen.emit(side)
