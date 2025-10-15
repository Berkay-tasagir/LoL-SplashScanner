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

    # Şampiyon splash bölgesi (üst kısım)
    SPLASH_ROI_Y0, SPLASH_ROI_Y1 = 0.025, 0.79

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
            
            for s_idx, (fx0, fx1) in enumerate(self.SPELL_BOXES, start=1):
                sx0, sx1 = int(pW * fx0), int(pW * fx1)
                crop = roi[:, max(0, sx0):min(pW, sx1)]
                fname = f"char{i+1}_spell{s_idx}.png"
                cv2.imwrite(os.path.join(self.OUTPUT_DIR, fname), crop)

                # --- Champion Splash Art kırp ---
                y0_s, y1_s = int(pH * self.SPLASH_ROI_Y0), int(pH * self.SPLASH_ROI_Y1)
                champ_crop = panel[y0_s:y1_s, :]
                cv2.imwrite(os.path.join(self.OUTPUT_DIR, f"char{i+1}_splash.png"), champ_crop)

            x += CARD_WIDTH_RATIO + CARD_GAP_RATIO
        debug_path = os.path.join(self.OUTPUT_DIR, "debug_full.png")
        cv2.imwrite(debug_path, debug_img)
        print(f"[✓] Debug görsel kaydedildi: {debug_path}")
        self._compare_with_assets()
        for s_idx, (fx0, fx1) in enumerate(self.SPELL_BOXES, start=1):
            sx0, sx1 = int(pW * fx0), int(pW * fx1)
            crop = roi[:, max(0, sx0):min(pW, sx1)]
            fname = f"char{i+1}_spell{s_idx}.png"
            cv2.imwrite(os.path.join(self.OUTPUT_DIR, fname), crop)

            # --- Champion Splash Art kırp ---
            y0_s, y1_s = int(pH * self.SPLASH_ROI_Y0), int(pH * self.SPLASH_ROI_Y1)
            champ_crop = panel[y0_s:y1_s, :]
            cv2.imwrite(os.path.join(self.OUTPUT_DIR, f"char{i+1}_splash.png"), champ_crop)
        self._compare_splash_with_loading()


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

    @staticmethod
    def compare_images(img_path_1, img_path_2):
        """
        İki görüntü arasındaki benzerliği hesaplar (yüzde olarak döner).
        Görselleri 128x128'e ölçekler, gri yapar, MSE ve yapısal farkları kullanır.
        """
        try:
            img1 = cv2.imread(img_path_1)
            img2 = cv2.imread(img_path_2)

            if img1 is None or img2 is None:
                return -1.0

            # Gri tonlamaya çevir
            img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

            # Aynı boyuta getir
            img1 = cv2.resize(img1, (128, 128))
            img2 = cv2.resize(img2, (128, 128))

            # MSE (Mean Squared Error)
            err = np.sum((img1.astype("float") - img2.astype("float")) ** 2)
            err /= float(img1.shape[0] * img1.shape[1])

            # Basit benzerlik skoru (0–100 arası)
            score = max(0, 100 - err / 50.0)
            return round(score, 1)

        except Exception as e:
            print(f"[compare_images error] {e}")
            return -1.0
    # --- splash karşılaştırma ---
    def _compare_splash_with_loading(self):
        import glob, cv2, os

        print("\n========== SPLASH SONUCU ==========")

        base = os.path.dirname(__file__)
        candidates = [
            os.path.join(base, "assets", "loading"),
            os.path.join(base, "loading"),
        ]
        loading_dir = None
        for p in candidates:
            if os.path.isdir(p):
                loading_dir = p
                break
        if loading_dir is None:
            print("[-] 'loading' klasörü bulunamadı. Şu yollar denendi:")
            for c in candidates: print("   ", c)
            print("=================================\n")
            return

        # İndeks yoksa bir kez oluştur
        if not getattr(self, "_loading_index", None):
            self._build_loading_index(loading_dir)
            if not self._loading_index:
                print("[-] loading klasöründe uygun görsel yok (jpg/jpeg/png).")
                print("=================================\n")
                return

        # Splash dosyalarını tara
        for i in range(1, 6):
            splash_path = os.path.join(self.OUTPUT_DIR, f"char{i}_splash.png")
            if not os.path.exists(splash_path):
                print(f"{os.path.basename(splash_path)} -> yok")
                continue

            splash = cv2.imread(splash_path)
            if splash is None:
                print(f"{os.path.basename(splash_path)} -> okunamadı")
                continue

            name, score = self._best_match_splash(splash)
            if score < 75:
                name = "?"
            print(f"{os.path.basename(splash_path)} -> {name} ({score:.1f})")

            # GUI’ye karakter PP'sini gönder
            try:
                char_idx = i - 1
                if 0 <= char_idx < len(self.cards):
                    card = self.cards[char_idx]
                    # champion klasöründen base skin PP'sini bul
                    if name != "?":
                        pp_path = os.path.join(os.path.dirname(__file__), "champion", f"{name}.png")
                        if os.path.exists(pp_path):
                            card.set_champion_icon(pp_path)
                        else:
                            card.set_champion_icon(None)
                    else:
                        card.set_champion_icon(None)
            except Exception as e:
                print(f"[PP yükleme hatası] {e}")

        print("=================================\n")

    def _best_match_splash(self, splash_bgr):
        import numpy as np, cv2, os
        if not getattr(self, "_loading_index", None):
            return "?", -1.0

        imr, gray = self._prep_for_match(splash_bgr)
        ph = self._phash(gray)
        hist = self._hist_hsv(imr)

        # --- 1) Hızlı eleme (pHash + hist) ---
        prelim = []
        for it in self._loading_index:
            if it["phash"] is None or it["hist"] is None:
                continue
            ham = self._hamming(ph, it["phash"])  # düşük iyi
            hsc = cv2.compareHist(hist.astype(np.float32),
                                it["hist"].astype(np.float32),
                                cv2.HISTCMP_CORREL)  # yüksek iyi
            prelim_score = (hsc * 100.0) - (ham * 1.4)
            prelim.append((prelim_score, it))
        if not prelim:
            return "?", -1.0

        prelim.sort(key=lambda x: x[0], reverse=True)
        candidates = [it for _, it in prelim[:20]]  # top-20 aday

        # --- 2) Kesin eşleşme (KNN + RANSAC) ---
        kp_s, des_s = self._orb.detectAndCompute(gray, None)
        if des_s is None or len(des_s) == 0:
            return "?", -1.0

        champion_scores = {}  # { "Pantheon": en iyi skor, "Ekko": ... }

        for it in candidates:
            des_t = it["des"]
            if des_t is None or len(des_t) == 0:
                continue

            knn = self._bf.knnMatch(des_s, des_t, k=2)
            good = []
            for m, n in knn:
                if m.distance < 0.75 * n.distance:
                    good.append(m)
            if len(good) < 8:
                continue

            src_pts = np.float32([kp_s[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([it["kp"][m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            inliers = int(mask.sum()) if mask is not None else 0
            inlier_ratio = inliers / max(1, len(good))

            hsc = cv2.compareHist(hist.astype(np.float32),
                                it["hist"].astype(np.float32),
                                cv2.HISTCMP_CORREL)
            hsc = (hsc + 1.0) * 50.0
            final_score = 0.8 * (inlier_ratio * 100.0) + 0.2 * hsc

            # --- 3) Şampiyon ismini dosya adından ayıkla ---
            champ_name = os.path.basename(it["path"]).split("_")[0]
            champion_scores[champ_name] = max(champion_scores.get(champ_name, -1.0), final_score)

        if not champion_scores:
            return "?", -1.0

        # --- 4) En yüksek puanlı şampiyonu seç ---
        best_champ = max(champion_scores, key=champion_scores.get)
        best_score = champion_scores[best_champ]
        return best_champ, round(float(best_score), 1)


    @staticmethod
    def _phash(gray_8u):
        # 32x32 -> DCT -> 8x8 düşük frekans pHash (64-bit)
        import cv2, numpy as np
        g = cv2.resize(gray_8u, (32, 32), interpolation=cv2.INTER_AREA)
        g = np.float32(g)
        dct = cv2.dct(g)
        dct_low = dct[:8, :8]
        med = np.median(dct_low[1:, 1:])  # DC hariç
        bits = (dct_low > med).astype(np.uint8)
        return bits.flatten()

    @staticmethod
    def _hamming(b1, b2):
        # b1,b2: 64 uzunlukta 0/1 vektör
        import numpy as np
        return int(np.sum(b1 ^ b2))

    @staticmethod
    def _hist_hsv(img_bgr):
        import cv2, numpy as np
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0,1,2], None, [8,8,8], [0,180,0,256,0,256])
        hist = cv2.normalize(hist, hist).flatten()
        return hist

    def _build_loading_index(self, loading_dir):
        import glob, cv2, os
        self._loading_index = []
        self._orb = cv2.ORB_create(nfeatures=1200)
        # KNN + ratio test için crossCheck=False
        self._bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

        files = []
        files += glob.glob(os.path.join(loading_dir, "*.jpg"))
        files += glob.glob(os.path.join(loading_dir, "*.jpeg"))
        files += glob.glob(os.path.join(loading_dir, "*.png"))

        for p in files:
            img = cv2.imread(p)
            if img is None:
                continue
            imr, gray = self._prep_for_match(img)
            # pHash + HSV hist (hızlı eleme için)
            ph = self._phash(gray)
            hist = self._hist_hsv(imr)
            kp, des = self._orb.detectAndCompute(gray, None)
            self._loading_index.append({"path": p, "phash": ph, "hist": hist, "kp": kp, "des": des})

    @staticmethod
    def _prep_for_match(img_bgr):
        import cv2, numpy as np
        h, w = img_bgr.shape[:2]
        # orta-%70 yatay, üst-%75 dikey (yüz/omuz odak)
        x0 = int(w * 0.15); x1 = int(w * 0.85)
        y0 = int(h * 0.05); y1 = int(h * 0.80)
        roi = img_bgr[y0:y1, x0:x1]

        # boyut sabitle
        roi = cv2.resize(roi, (256, 256), interpolation=cv2.INTER_AREA)

        # kontrast/aydınlık dengeleme (CLAHE, LAB-L kanal)
        lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
        L, A, B = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        L = clahe.apply(L)
        lab = cv2.merge([L,A,B])
        roi = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        return roi, gray
