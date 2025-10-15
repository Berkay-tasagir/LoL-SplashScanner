from PyQt5 import QtWidgets, QtCore, QtGui
from spell_components import SpellButton
import os
import json

class ChampionSelectWindow(QtWidgets.QWidget):
    """Elle şampiyon seçme penceresi"""
    champion_selected = QtCore.pyqtSignal(str)

    def __init__(self, champion_dir):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.Popup)
        self.setFixedSize(280, 320)
        self.champion_dir = champion_dir

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Şampiyon ara...")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.list = QtWidgets.QListWidget()
        self.list.itemClicked.connect(self._select)
        layout.addWidget(self.list)

        self._load_all()

    def _load_all(self):
        """champion klasöründeki tüm .png’leri yükler"""
        self.all_names = []
        for f in os.listdir(self.champion_dir):
            if f.endswith(".png"):
                name = os.path.splitext(f)[0]
                self.all_names.append(name)
        self._populate(self.all_names)

    def _populate(self, names):
        self.list.clear()
        for n in sorted(names):
            self.list.addItem(n)

    def _filter(self, text):
        filtered = [n for n in self.all_names if text.lower() in n.lower()]
        self._populate(filtered)

    def _select(self, item):
        name = item.text()
        self.champion_selected.emit(name)
        self.close()


class CharacterCard(QtWidgets.QFrame):
    def _on_icon_click(self, event):
        """Kırmızı kareye tıklayınca seçim penceresini aç."""
        from PyQt5 import QtGui
        champion_dir = os.path.join(os.path.dirname(__file__), "champion")
        if not os.path.isdir(champion_dir):
            print("champion klasörü bulunamadı.")
            return

        win = ChampionSelectWindow(champion_dir)
        win.champion_selected.connect(self._apply_manual_choice)
        pos = self.mapToGlobal(QtCore.QPoint(0, 0))
        win.move(pos.x() + self.width()//2 - win.width()//2,
                pos.y() - win.height())
        win.show()
        self._chooser = win  # referans tut (GC önle)

    def _apply_manual_choice(self, name):
        # karakter değişince varsa sayaç sıfırlansın
        self.ult_timer.stop()
        self.ult_timer_label.hide()
        self.ult_timer_value = 100
        self.ult_timer_running = False

        champion_dir = os.path.join(os.path.dirname(__file__), "champion")
        img_path = os.path.join(champion_dir, f"{name}.png")
        if os.path.exists(img_path):
            self.set_champion_icon(img_path)
        else:
            print(f"{name}.png bulunamadı")
        self.current_champion = name

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

        # --- Ulti seviye kutuları ---
        self.ult_level_buttons = []
        levels_frame = QtWidgets.QFrame(self)
        levels_layout = QtWidgets.QHBoxLayout(levels_frame)
        levels_layout.setSpacing(4)
        levels_layout.setContentsMargins(0, 4, 0, 0)

        for i in range(1, 4):
            btn = QtWidgets.QPushButton(str(i))
            btn.setFixedSize(30, 30)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #b32020;
                    color: white;
                    border: 2px solid black;
                    font: bold 14px Arial;
                }
                QPushButton:hover {
                    background-color: #ff4040;
                }
            """)
            btn.clicked.connect(lambda _, lvl=i: self._start_timer_for_level(lvl))
            self.ult_level_buttons.append(btn)
            levels_layout.addWidget(btn)
            # self.icon zaten layout'ta olduğu için pozisyonu başlangıçta bilinmiyor,
            # bu yüzden sadece sabit yerleştirme yapıyoruz, daha sonra resizeEvent'ta güncellenecek
        # --- 1-2-3 seviye kutuları tamamlandıktan sonra ---
        levels_frame.setParent(self)
        self.levels_frame = levels_frame
        levels_frame.move(0, 0)  # başlangıçta konum ver

        # kırmızı daire (karakter)
        self.icon = QtWidgets.QLabel()
       # --- Ulti sayaç etiketi (doğru sıralama) ---
        self.ult_timer_label = QtWidgets.QLabel("100", self.icon)
        self.ult_timer_label.setAlignment(QtCore.Qt.AlignCenter)
        self.ult_timer_label.setGeometry(0, 0, 100, 100)
        self.ult_timer_label.setStyleSheet("""
            background-color: rgba(0, 255, 0, 80);
            color: white;
            font: bold 26px Arial;
            border: none;
        """)
        self.ult_timer_label.hide()
        self.ult_timer_value = 100
        self.ult_timer_running = False

        # Sayaç güncelleme için timer
        self.ult_timer = QtCore.QTimer()
        self.ult_timer.timeout.connect(self._update_ult_timer)

        # PP’ye tıklayınca sayaç başlasın/dursun
        self.icon.setFixedSize(100, 100)
        self.icon.setStyleSheet("background:#b32020; border:2px solid black; border-radius:0px;")
        self.icon.mousePressEvent = self._on_icon_pressed
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

    def set_champion_icon(self, img_path):
        """Karakter PP’sini gösterir; yoksa kırmızı kare boş kalır."""
        if img_path and os.path.exists(img_path):
            pix = QtGui.QPixmap(img_path)
            pix = pix.scaled(
                self.icon.width(), self.icon.height(),
                QtCore.Qt.KeepAspectRatioByExpanding,
                QtCore.Qt.SmoothTransformation
            )
            self.icon.setPixmap(pix)
            self.icon.setStyleSheet("border:2px solid black; border-radius:0px; background:none;")
        else:
            self.icon.clear()
            self.icon.setStyleSheet("background:#b32020; border:2px solid black; border-radius:0px;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "levels_frame") and hasattr(self, "icon"):
            x = self.icon.x()
            y = self.icon.y() + self.icon.height() + 4
            w = self.icon.width()
            self.levels_frame.setGeometry(x, y, w, 30)

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

    def _on_ult_click(self, event):
        self.ult_timer_label.raise_()
        """PP'ye tıklayınca ult cooldown sayacı başlat/durdur"""
        # Her tıklamada sayaç resetlenir ve baştan başlar
        self.ult_timer.stop()                # varsa eski timer'ı durdur
        self.ult_timer_value = 100           # yeniden başlat
        self.ult_timer_label.setText(str(self.ult_timer_value))
        self.ult_timer_label.show()
        self.ult_timer_label.raise_()
        self.ult_timer.start(1000)
        self.ult_timer_running = True

    def _update_ult_timer(self):
        self.ult_timer_value -= 1
        if self.ult_timer_value <= 0:
            self.ult_timer.stop()
            self.ult_timer_label.hide()
            self.ult_timer_running = False
            return
        self.ult_timer_label.setText(str(self.ult_timer_value))

    def _on_icon_pressed(self, event):
        """Mod durumuna göre davranış belirler."""
        if self.mode == "edit":
            # düzenleme modunda şampiyon seçimi penceresini aç
            champion_dir = os.path.join(os.path.dirname(__file__), "champion")
            if not os.path.isdir(champion_dir):
                print("champion klasörü bulunamadı.")
                return

            win = ChampionSelectWindow(champion_dir)
            win.champion_selected.connect(self._apply_manual_choice)
            pos = self.mapToGlobal(QtCore.QPoint(0, 0))
            win.move(pos.x() + self.width() // 2 - win.width() // 2,
                    pos.y() - win.height())
            win.show()
            self._chooser = win
        else:
            # use modunda her tıklamada sayaç yeniden başlasın
            self._reset_and_start_timer()

    def _get_ultimate_cd(self, champ_name):
        """Şampiyonun JSON dosyasını okuyup R büyüsünün ilk cooldown değerini döner."""
        try:
            path = os.path.join(os.path.dirname(__file__), "char_json", "champion_json", f"{champ_name}.json")
            if not os.path.exists(path):
                print(f"[!] JSON bulunamadı: {path}")
                return 100  # fallback

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            spells = data["data"][champ_name]["spells"]
            for s in spells:
                if s["id"].endswith("R"):
                    cd = s["cooldown"][0]
                    return int(cd)
            return 100
        except Exception as e:
            print(f"[JSON read error] {e}")
            return 100

    def _get_ultimate_cd_by_level(self, champ_name, level):
        """Belirtilen ulti seviyesinin cooldown süresini döndürür."""
        try:
            path = os.path.join(os.path.dirname(__file__), "char_json", "champion_json", f"{champ_name}.json")
            if not os.path.exists(path):
                print(f"[!] JSON bulunamadı: {path}")
                return None

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            spells = data["data"][champ_name]["spells"]
            for s in spells:
                if s["id"].endswith("R"):
                    cds = s["cooldown"]
                    idx = max(0, min(level - 1, len(cds) - 1))
                    return cds[idx]
            return None
        except Exception as e:
            print(f"[JSON read error] {e}")
            return None

    def _reset_and_start_timer(self):
        """Her tıklamada sayaç sıfırlanır ve karakterin ulti süresinden başlar."""
        self.ult_timer.stop()

        # Şampiyon ismini al
        champ_name = getattr(self, "current_champion", None)
        if champ_name:
            cd_value = self._get_ultimate_cd(champ_name)
        else:
            cd_value = 100  # eğer şampiyon atanmadıysa varsayılan

        self.ult_timer_value = cd_value
        self.ult_timer_label.setText(str(self.ult_timer_value))
        self.ult_timer_label.show()
        self.ult_timer_label.raise_()
        self.ult_timer.start(1000)
        self.ult_timer_running = True

    def _start_timer_for_level(self, level):
        """Seçilen ulti seviyesinin cooldown süresinden sayaç başlatır."""
        champ_name = getattr(self, "current_champion", None)
        if not champ_name:
            print("[-] Önce bir şampiyon seçmelisin.")
            return

        cd_value = self._get_ultimate_cd_by_level(champ_name, level)
        if cd_value is None:
            cd_value = 100

        # timer'ı sıfırla ve başlat
        self.ult_timer.stop()
        self.ult_timer_value = int(cd_value)
        self.ult_timer_label.setText(str(self.ult_timer_value))
        self.ult_timer_label.show()
        self.ult_timer_label.raise_()
        self.ult_timer.start(1000)
        self.ult_timer_running = True
