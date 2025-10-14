from PyQt5 import QtWidgets, QtGui, QtCore
import os

# --- ikon klasörü ---
ICON_DIR = os.path.join(os.path.dirname(__file__), "assets", "icons")

SPELLS = [
    "barrier", "cleanse", "exhaust", "flash", "ghost",
    "heal", "ignite", "smite", "teleport"
]

COOLDOWNS = {
    "flash": 300, "ignite": 180, "smite": 15, "heal": 240,
    "barrier": 180, "cleanse": 210, "ghost": 210,
    "exhaust": 210, "teleport": 360
}


# 🔹 Spell seçim penceresi
class SpellSelectWindow(QtWidgets.QWidget):
    spell_selected = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.Popup)
        self.setFixedSize(300, 200)
        grid = QtWidgets.QGridLayout(self)
        grid.setSpacing(8)
        grid.setContentsMargins(10, 10, 10, 10)

        for i, spell in enumerate(SPELLS):
            btn = QtWidgets.QPushButton()
            icon_path = self._find_icon(spell)
            if icon_path:
                btn.setIcon(QtGui.QIcon(icon_path))
                btn.setIconSize(QtCore.QSize(48, 48))
            btn.setFixedSize(56, 56)
            btn.setStyleSheet("background:#2c2c2c; border-radius:6px;")
            btn.clicked.connect(lambda _, s=spell: self._choose(s))
            grid.addWidget(btn, i // 5, i % 5)

    def _find_icon(self, spell):
        for c in [f"{spell}.png", f"{spell}.png.png"]:
            p = os.path.join(ICON_DIR, c)
            if os.path.exists(p):
                return p
        return None

    def _choose(self, spell):
        self.spell_selected.emit(spell)
        self.close()


# 🔹 Timer kutusu (ikon altındaki sayaç)
class TimerBox(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        self.remaining = 0
        self.cooldown_time = 0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)

        self.setFixedSize(48, 22)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setText("0")
        self._update_style(active=False)

    def start(self, spell: str):
        self.cooldown_time = COOLDOWNS.get(spell, 60)
        self.remaining = self.cooldown_time
        self._update_style(active=True)
        self._update_label()
        self.timer.start(1000)

    def stop(self):
        self.timer.stop()
        self.remaining = 0
        self._update_style(active=False)
        self.setText("0")

    def _tick(self):
        self.remaining -= 1
        if self.remaining <= 0:
            self.stop()
        else:
            self._update_label()

    def _update_label(self):
        self.setText(str(self.remaining))

    def _update_style(self, active=False):
        color = "lime" if active else "red"
        self.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                color: {color};
                font-weight: bold;
                font-size: 14px;
            }}
        """)


# 🔹 Spell butonu (ikon + alt sayaç)
class SpellButton(QtWidgets.QWidget):
    spell_changed = QtCore.pyqtSignal(str)

    def __init__(self, default_spell="flash"):
        super().__init__()
        self.current_spell = default_spell
        self.mode = "edit"

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        # ikon butonu
        self.button = QtWidgets.QPushButton()
        self.button.setFixedSize(48, 48)
        self.button.setStyleSheet("background:#2e2e2e; border:none; border-radius:6px;")
        self.button.setIconSize(QtCore.QSize(44, 44))
        layout.addWidget(self.button, alignment=QtCore.Qt.AlignCenter)

        # sayaç
        self.timer_box = TimerBox()
        layout.addWidget(self.timer_box, alignment=QtCore.Qt.AlignCenter)

        self._update_icon()
        self.button.clicked.connect(self._handle_click)

    def set_mode(self, mode: str):
        self.mode = mode

    def _find_icon(self, spell):
        for n in [f"{spell}.png", f"{spell}.png.png"]:
            path = os.path.join(ICON_DIR, n)
            if os.path.exists(path):
                return path
        return None

    def _update_icon(self):
        path = self._find_icon(self.current_spell)
        if path:
            self.button.setIcon(QtGui.QIcon(path))
            self.button.setText("")
        else:
            self.button.setText(self.current_spell.capitalize())

    def _handle_click(self):
        if self.mode == "use":
            self.timer_box.start(self.current_spell)
        else:
            self._open_selector()

    def _open_selector(self):
        self.selector = SpellSelectWindow()
        self.selector.spell_selected.connect(self.set_spell)
        self.selector.move(QtGui.QCursor.pos())
        self.selector.show()

    def set_spell(self, spell):
        self.current_spell = spell
        self._update_icon()
        self.timer_box.stop()
        self.spell_changed.emit(spell)

    def set_editable(self, editable: bool):
        self.editable = editable
        if editable:
            self.setCursor(QtCore.Qt.PointingHandCursor)
            self.setStyleSheet("border: 2px dashed #ff9900;")
        else:
            self.setCursor(QtCore.Qt.ArrowCursor)
            self.setStyleSheet("border: none;")