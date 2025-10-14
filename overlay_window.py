from PyQt5 import QtWidgets, QtCore, QtGui
from character_card import CharacterCard
from controls import ModeSwitch, ScanWithSide
import os, time, pyautogui, cv2
from datetime import datetime
import numpy as np


class SelectionOverlay(QtWidgets.QWidget):
    def __init__(self, fixed_w=1392, fixed_h=448, start_center=QtCore.QPoint(960, 540)):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                            QtCore.Qt.WindowStaysOnTopHint |
                            QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.dragging = False
        self.size_x = fixed_w
        self.size_y = fixed_h
        self.center = start_center
        self.resize(QtWidgets.QApplication.primaryScreen().size())
        self.showFullScreen()


    def event(self, e):
        # Kutunun içindeysek (drag aktif), event'i normal işle
        if e.type() in (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseMove, QtCore.QEvent.MouseButtonRelease):
            rect = QtCore.QRect(self.center.x()-self.size_x//2,
                                self.center.y()-self.size_y//2,
                                self.size_x, self.size_y)
            if rect.contains(QtGui.QCursor.pos()):
                return super().event(e)  # kutunun içindeyse overlay hareket eder
            else:
                # dışarıdaysak, ama eğer fareyi bıraktıysak dragging'i sıfırla
                if e.type() == QtCore.QEvent.MouseButtonRelease:
                    self.dragging = False
                return False  # olayı alt pencereye geçir
        return super().event(e)


    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 120))
        rect = QtCore.QRect(self.center.x()-self.size_x//2,
                            self.center.y()-self.size_y//2,
                            self.size_x, self.size_y)
        pen = QtGui.QPen(QtGui.QColor(0,255,0), 3)
        p.setPen(pen)
        p.drawRect(rect)

    def mousePressEvent(self, e):
        rect = QtCore.QRect(self.center.x()-self.size_x//2,
                            self.center.y()-self.size_y//2,
                            self.size_x, self.size_y)
        if rect.contains(e.pos()):
            self.dragging = True
            self.drag_offset = e.pos() - rect.topLeft()

    def mouseMoveEvent(self, e):
        if self.dragging:
            tl = e.pos() - self.drag_offset
            self.center = QtCore.QPoint(tl.x()+self.size_x//2, tl.y()+self.size_y//2)
            self.update()

    def mouseReleaseEvent(self, e): 
        self.dragging = False

    def get_rect(self):
        return QtCore.QRect(self.center.x()-self.size_x//2,
                            self.center.y()-self.size_y//2,
                            self.size_x, self.size_y)


class OverlayWindow(QtWidgets.QWidget):
    NUM_PANELS = 5
    SPELL_ROI_Y0, SPELL_ROI_Y1 = 0.82, 0.88
    SPELL_BOXES = [
        (0.680, 0.790),
        (0.810, 0.930),
    ]
    INNER_TRIM_TOP  = 0.05
    INNER_TRIM_BOT  = 0.05
    OUTPUT_DIR = "spells_output"

    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                            QtCore.Qt.WindowStaysOnTopHint |
                            QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self._drag = False

        shell = QtWidgets.QFrame()
        shell.setStyleSheet("QFrame{background:rgba(0,0,0,0.6);border:none;border-radius:10px;}")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10,10,10,10)
        root.addWidget(shell)

        layout = QtWidgets.QVBoxLayout(shell)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(18)

        # --- üst satır: karakter kartları ---
        line = QtWidgets.QHBoxLayout()
        line.setSpacing(8)
        self.cards = [CharacterCard() for _ in range(5)]
        for c in self.cards: 
            line.addWidget(c)
        layout.addLayout(line)

        # --- alt satır: Tara + Mod Seçimi ---
        bottom = QtWidgets.QHBoxLayout()
        self.scan = ScanWithSide()
        self.scan.btn_scan.clicked.connect(self._on_scan_click)
        bottom.addWidget(self.scan, alignment=QtCore.Qt.AlignLeft)
        bottom.addStretch()
        self.mode_switch = ModeSwitch()
        bottom.addWidget(self.mode_switch, alignment=QtCore.Qt.AlignRight)
        layout.addLayout(bottom)

        # --- mod geçiş sinyali ---
        self.mode_switch.modeChanged.connect(self._on_mode_changed)

        self._scan_overlay = None

    # pencere sürükleme
    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag = True
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()
    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() == QtCore.Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)
            e.accept()
    def mouseReleaseEvent(self, e): 
        self._drag = False

    # --- ModeSwitch sinyalini işleme ---
    def _on_mode_changed(self, is_edit_mode: bool):
        """Düzenleme / Kullanma moduna geçildiğinde tüm kartlara aktar."""
        mode = "edit" if is_edit_mode else "use"
        for card in self.cards:
            if hasattr(card, "set_mode"):
                card.set_mode(mode)
            if hasattr(card, "set_editable"):
                card.set_editable(is_edit_mode)

    # --- Tara butonu davranışı ---
    def _on_scan_click(self):
        if self._scan_overlay and self._scan_overlay.isVisible():
            rect = self._scan_overlay.get_rect()
            self._scan_overlay.close()
            self._scan_overlay = None
            self._capture_and_save_spells(rect)
            return
        self._scan_overlay = SelectionOverlay()
        self._scan_overlay.show()

    def _capture_and_save_spells(self, rect: QtCore.QRect):
        # Arayüzü gizle -> ss al -> geri göster
        self.hide()
        QtWidgets.QApplication.processEvents()
        time.sleep(0.35)

        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        ss = pyautogui.screenshot(region=(x, y, w, h))

        self.show()
        img = cv2.cvtColor(np.array(ss), cv2.COLOR_RGB2BGR)

        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        self._extract_and_save(img)
        print(f"[+] Speller kaydedildi -> {self.OUTPUT_DIR}")


    def _extract_and_save(self, img_bgr):
        img = img_bgr if len(img_bgr.shape) == 3 else cv2.cvtColor(img_bgr, cv2.COLOR_GRAY2BGR)
        H, W = img.shape[:2]
        CARD_WIDTH_RATIO = 0.176
        CARD_GAP_RATIO   = 0.030
        debug_img = img.copy()
        x = 0
        for i in range(self.NUM_PANELS):
            x0 = int(W * x)
            x1 = int(W * (x + CARD_WIDTH_RATIO))
            panel = img[:, x0:x1]
            pH, pW = panel.shape[:2]
            cv2.rectangle(debug_img, (x0, 0), (x1, H), (0, 255, 0), 2)
            y0, y1 = int(pH * self.SPELL_ROI_Y0), int(pH * self.SPELL_ROI_Y1)
            roi = panel[y0:y1, :]
            cv2.rectangle(debug_img, (x0, y0), (x1, y1), (255, 0, 0), 2)
            for s_idx, (fx0, fx1) in enumerate(self.SPELL_BOXES, start=1):
                sx0, sx1 = int(pW * fx0), int(pW * fx1)
                abs_x0, abs_x1 = x0 + sx0, x0 + sx1
                cv2.rectangle(debug_img, (abs_x0, y0), (abs_x1, y1), (0, 165, 255), 2)
                crop = roi[:, max(0, sx0):min(pW, sx1)]
                fname = f"char{i+1}_spell{s_idx}.png"
                cv2.imwrite(os.path.join(self.OUTPUT_DIR, fname), crop)
            x += CARD_WIDTH_RATIO + CARD_GAP_RATIO
        debug_path = os.path.join(self.OUTPUT_DIR, "debug_full.png")
        cv2.imwrite(debug_path, debug_img)
        print(f"[✓] Debug görsel kaydedildi: {debug_path}")
        self._compare_with_assets()

    # --- ikon eşleştirme (ORB + Histogram) ---
    def _compare_with_assets(self):
        import glob
        icons_dir = os.path.join(os.path.dirname(__file__), "assets", "icons")
        spell_imgs = sorted(glob.glob(os.path.join(self.OUTPUT_DIR, "char*_spell*.png")))
        asset_imgs = sorted(glob.glob(os.path.join(icons_dir, "*.png")))

        if not spell_imgs:
            print("[-] spells_output klasöründe hiç kırpılmış görsel yok.")
            return

        orb = cv2.ORB_create(nfeatures=500)
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        print("\n========== SPELL SONUCU ==========")

        for path in spell_imgs:
            img = cv2.imread(path)
            if img is None:
                continue
            img_resized = cv2.resize(img, (96, 96))
            img_gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
            kp1, des1 = orb.detectAndCompute(img_gray, None)
            best_match, best_score = None, -1.0

            for asset in asset_imgs:
                icon = cv2.imread(asset)
                if icon is None: continue
                icon_resized = cv2.resize(icon, (96, 96))
                icon_gray = cv2.cvtColor(icon_resized, cv2.COLOR_BGR2GRAY)
                kp2, des2 = orb.detectAndCompute(icon_gray, None)
                if des1 is None or des2 is None: continue
                matches = bf.match(des1, des2)
                if len(matches) == 0: continue
                orb_score = np.mean([m.distance for m in matches])
                # LAB histogram farkı
                img_lab = cv2.cvtColor(img_resized, cv2.COLOR_BGR2LAB)
                icon_lab = cv2.cvtColor(icon_resized, cv2.COLOR_BGR2LAB)
                hist1 = cv2.calcHist([img_lab],[0,1,2],None,[8,8,8],[0,256,0,256,0,256])
                hist2 = cv2.calcHist([icon_lab],[0,1,2],None,[8,8,8],[0,256,0,256,0,256])
                hist1 = cv2.normalize(hist1, hist1).flatten()
                hist2 = cv2.normalize(hist2, hist2).flatten()
                hist_score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
                final_score = (100 - orb_score) * 0.5 + (hist_score * 100) * 0.5
                if final_score > best_score:
                    best_score, best_match = final_score, asset

            name = os.path.basename(best_match).replace(".png", "") if best_match else "?"
            print(f"{os.path.basename(path)} -> {name} ({best_score:.1f})")

            # GUI'ye yerleştir
            parts = os.path.basename(path).replace(".png", "").split("_")
            try:
                char_idx = int(parts[0].replace("char", "")) - 1
                spell_idx = int(parts[1].replace("spell", "")) - 1
            except:
                char_idx, spell_idx = 0, 0

            if 0 <= char_idx < len(self.cards):
                card = self.cards[char_idx]
                if spell_idx == 0:
                    card.spell1.set_spell(name)
                elif spell_idx == 1:
                    card.spell2.set_spell(name)

        print("=================================\n")
