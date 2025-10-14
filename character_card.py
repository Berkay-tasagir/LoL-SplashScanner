from PyQt5 import QtWidgets, QtCore, QtGui
from spell_components import SpellButton


class CharacterCard(QtWidgets.QFrame):
    def __init__(self, w=170, h=220):
        super().__init__()
        self.setFixedSize(w, h)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent; border: none;")
        self.mode = "edit"

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        outer.setAlignment(QtCore.Qt.AlignBottom)

        self.content = QtWidgets.QWidget()
        self.content.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        outer.addWidget(self.content)

        v = QtWidgets.QVBoxLayout(self.content)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        v.setAlignment(QtCore.Qt.AlignBottom)

        # spell satırı
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        row.setAlignment(QtCore.Qt.AlignCenter)

        self.spell1 = SpellButton("flash")
        self.spell2 = SpellButton("ignite")

        row.addWidget(self.spell1)
        row.addWidget(self.spell2)
        v.addLayout(row)

        # kırmızı daire (karakter)
        self.icon = QtWidgets.QLabel()
        self.icon.setFixedSize(100, 100)
        self.icon.setStyleSheet("background:#b32020; border:2px solid black; border-radius:50px;")
        v.addWidget(self.icon, alignment=QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom)

        outer.addItem(QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        # ok butonu
        self.arrow_btn = QtWidgets.QPushButton("▼")
        self.arrow_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.arrow_btn.setFixedHeight(20)
        self.arrow_btn.setStyleSheet("""
            QPushButton {
                background:#505050; color:white;
                font-weight:bold; font-size:18px;
                border:none; border-top:2px solid rgba(255,255,255,0.3);
                border-bottom-left-radius:4px; border-bottom-right-radius:4px;
            }
            QPushButton:hover { background:#5a5a5a; }
        """)
        outer.addWidget(self.arrow_btn, alignment=QtCore.Qt.AlignBottom)
        self._open = True
        self.arrow_btn.clicked.connect(self._toggle)

    def _toggle(self):
        self._open = not self._open
        self.arrow_btn.setText("▲" if self._open else "▼")
        self.content.setVisible(self._open)

    def set_mode(self, mode: str):
        self.mode = mode
        self.spell1.set_mode(mode)
        self.spell2.set_mode(mode)
        
    def set_editable(self, editable: bool):
        """Bu karakterin iki spelli de düzenleme moduna göre güncellenir."""
        self.spell1.set_editable(editable)
        self.spell2.set_editable(editable)