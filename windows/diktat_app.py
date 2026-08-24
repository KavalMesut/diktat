import sys
import os
import time
import threading
import math
import ctypes
import winsound
from pathlib import Path
import numpy as np
import sounddevice as sd
import pyperclip
from pynput import keyboard as pynput_keyboard

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QPoint
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QSystemTrayIcon, QMenu, QDialog, QLineEdit, QComboBox,
    QCheckBox, QPushButton, QTextEdit, QGroupBox, QMessageBox
)
from PyQt6.QtGui import QIcon, QPainter, QColor, QFont, QPen, QBrush, QPixmap, QAction

from .config import ConfigManager, is_autostart_enabled, set_autostart
from .api_client import AIClient

# ---------------------------------------------------------
# Windows API for Direct Paste (Ctrl+V)
# ---------------------------------------------------------
user32 = ctypes.windll.user32
VK_CONTROL = 0x11
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002

def windows_paste():
    """Direct Windows user32.keybd_event Ctrl+V injection."""
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_V, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

# ---------------------------------------------------------
# Signals Bridge (Thread-Safe Qt Signals)
# ---------------------------------------------------------
class AppSignals(QObject):
    toggle_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    status_changed = pyqtSignal(str, str)
    level_updated = pyqtSignal(float)
    error_occurred = pyqtSignal(str)
    text_processed = pyqtSignal(str, str)

# ---------------------------------------------------------
# Corner Floating HUD
# Theme Palette: #DF301C, #FF9100, #FFF1D1, #00B7CD
# ---------------------------------------------------------
class FloatingHUD(QWidget):
    def __init__(self, config_mgr: ConfigManager):
        super().__init__()
        self.config_mgr = config_mgr
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.state = "idle"
        self.status_text = "Hazır"
        self.elapsed_seconds = 0
        self.db_level = -90.0
        self.pulse_phase = 0.0

        self.setFixedSize(290, 54)
        self.reposition()

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(50)

    def reposition(self):
        screen = QApplication.primaryScreen().geometry()
        corner = self.config_mgr.get("overlay_corner", "bottom-right")
        margin_x = 30
        margin_y = 70

        if corner == "bottom-right":
            x = screen.width() - self.width() - margin_x
            y = screen.height() - self.height() - margin_y
        elif corner == "bottom-left":
            x = margin_x
            y = screen.height() - self.height() - margin_y
        elif corner == "top-right":
            x = screen.width() - self.width() - margin_x
            y = margin_y
        else:
            x = margin_x
            y = margin_y

        self.move(x, y)

    def update_animation(self):
        if self.isVisible():
            self.pulse_phase += 0.15
            self.update()

    def set_state(self, state: str, text: str = ""):
        self.state = state
        self.status_text = text
        if state == "recording":
            self.elapsed_seconds = 0
            self.reposition()
            self.show()
        elif state in ["transcribing", "cleaning"]:
            self.show()
        elif state == "done":
            self.show()
            QTimer.singleShot(1500, self.hide_if_done)
        elif state == "error":
            self.show()
            QTimer.singleShot(3500, self.hide_if_done)
        elif state == "idle":
            self.hide()
        self.update()

    def hide_if_done(self):
        if self.state in ["done", "error", "idle"]:
            self.hide()

    def set_timer(self, seconds: int):
        self.elapsed_seconds = seconds
        self.update()

    def set_db(self, db: float):
        self.db_level = db
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_rect = self.rect().adjusted(2, 2, -2, -2)
        # Deep dark background with subtle warm undertone
        painter.setBrush(QBrush(QColor(12, 18, 30, 245)))
        # Subtle #00B7CD / #25334d border
        painter.setPen(QPen(QColor(0, 183, 205, 140), 1.5))
        painter.drawRoundedRect(bg_rect, 25, 25)

        dot_x = 26
        dot_y = self.height() // 2
        pulse = (math.sin(self.pulse_phase) + 1.0) / 2.0

        if self.state == "recording":
            # #DF301C Glowing recording dot
            glow_radius = 7 + pulse * 5
            painter.setBrush(QBrush(QColor(223, 48, 28, int(70 + pulse * 130))))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(dot_x, dot_y), int(glow_radius), int(glow_radius))

            painter.setBrush(QBrush(QColor(223, 48, 28)))
            painter.drawEllipse(QPoint(dot_x, dot_y), 4, 4)

            m = self.elapsed_seconds // 60
            s = self.elapsed_seconds % 60
            time_str = f"{m:02d}:{s:02d}"

            # #FFF1D1 Cream timer text
            painter.setPen(QPen(QColor(255, 241, 209)))
            painter.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
            painter.drawText(46, dot_y + 4, time_str)

            # #FF9100 Orange sound level
            db_display = f"{self.db_level:.0f} dB" if self.db_level > -85 else "Konuşun..."
            painter.setPen(QPen(QColor(255, 145, 0)))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.drawText(102, dot_y + 4, f"• {db_display}")

        elif self.state == "transcribing":
            # #00B7CD Cyan indicator
            painter.setBrush(QBrush(QColor(0, 183, 205)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(dot_x, dot_y), 5, 5)

            painter.setPen(QPen(QColor(0, 183, 205)))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.drawText(46, dot_y + 4, "Yazıya çevriliyor...")

        elif self.state == "cleaning":
            # #FF9100 Orange indicator
            painter.setBrush(QBrush(QColor(255, 145, 0)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(dot_x, dot_y), 5, 5)

            painter.setPen(QPen(QColor(255, 145, 0)))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.drawText(46, dot_y + 4, "Metin temizleniyor...")

        elif self.state == "done":
            # #00B7CD Cyan checkmark dot with #FFF1D1 text
            painter.setBrush(QBrush(QColor(0, 183, 205)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(dot_x, dot_y), 5, 5)

            painter.setPen(QPen(QColor(255, 241, 209)))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(46, dot_y + 4, "✓ Yapıştırıldı")

        elif self.state == "error":
            # #DF301C Red indicator
            painter.setBrush(QBrush(QColor(223, 48, 28)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(dot_x, dot_y), 5, 5)

            painter.setPen(QPen(QColor(255, 241, 209)))
            painter.setFont(QFont("Segoe UI", 9))
            disp = (self.status_text[:22] + "..") if len(self.status_text) > 22 else self.status_text
            painter.drawText(46, dot_y + 4, disp)

# ---------------------------------------------------------
# Audio Recording Engine
# ---------------------------------------------------------
class AudioRecorder:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.is_recording = False
        self.audio_chunks = []
        self.stream = None

    def start(self):
        self.audio_chunks = []
        self.is_recording = True
        
        # Check default input device availability
        try:
            default_dev = sd.default.device
            if default_dev[0] == -1 or default_dev[0] is None:
                devices = sd.query_devices()
                valid_in = [i for i, d in enumerate(devices) if d.get('max_input_channels', 0) > 0 and d.get('hostapi', 0) in (0, 1, 2)]
                if not valid_in:
                    raise RuntimeError("Windows'ta aktif mikrofon bulunamadı! Lütfen mikrofonunuzu bağlayın veya Ses Ayarlarından etkinleştirin.")
        except Exception as check_err:
            if "aktif mikrofon bulunamadı" in str(check_err):
                raise check_err

        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                callback=self._audio_callback,
                blocksize=1024
            )
            self.stream.start()
        except Exception:
            try:
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=2,
                    dtype='float32',
                    callback=self._audio_callback_stereo,
                    blocksize=1024
                )
                self.stream.start()
            except Exception:
                raise RuntimeError("Mikrofon başlatılamadı! Windows Ses Ayarlarından veya Gizlilik İzinlerinden mikrofonun açık olduğundan emin olun.")

    def _audio_callback(self, indata, frames, time_info, status):
        if self.is_recording:
            self.audio_chunks.append(indata.copy())

    def _audio_callback_stereo(self, indata, frames, time_info, status):
        if self.is_recording:
            mono = np.mean(indata, axis=1, keepdims=True)
            self.audio_chunks.append(mono)

    def get_current_db(self) -> float:
        if not self.audio_chunks:
            return -90.0
        last_chunk = self.audio_chunks[-1]
        rms = np.sqrt(np.mean(last_chunk ** 2))
        if rms > 0:
            db = 20 * np.log10(rms)
            return max(-90.0, min(0.0, float(db)))
        return -90.0

    def stop(self) -> np.ndarray:
        self.is_recording = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        if self.audio_chunks:
            return np.concatenate(self.audio_chunks, axis=0).flatten()
        return np.array([], dtype='float32')

# ---------------------------------------------------------
# Global Keyboard Listener (Pynput Hook)
# ---------------------------------------------------------
class GlobalKeyListener:
    def __init__(self, signals: AppSignals):
        self.signals = signals
        self.ctrl_pressed = False
        self.alt_pressed = False
        self.last_trigger_time = 0
        self.listener = None

    def on_press(self, key):
        if key in (pynput_keyboard.Key.ctrl, pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r):
            self.ctrl_pressed = True
        elif key in (pynput_keyboard.Key.alt, pynput_keyboard.Key.alt_l, pynput_keyboard.Key.alt_r, pynput_keyboard.Key.alt_gr):
            self.alt_pressed = True
        elif key == pynput_keyboard.Key.space:
            now = time.time()
            if now - self.last_trigger_time < 0.35:
                return  # Debounce duplicate key events
            
            if self.ctrl_pressed and self.alt_pressed:
                self.last_trigger_time = now
                self.signals.cancel_requested.emit()
            elif self.ctrl_pressed:
                self.last_trigger_time = now
                self.signals.toggle_requested.emit()

    def on_release(self, key):
        if key in (pynput_keyboard.Key.ctrl, pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r):
            self.ctrl_pressed = False
        elif key in (pynput_keyboard.Key.alt, pynput_keyboard.Key.alt_l, pynput_keyboard.Key.alt_r, pynput_keyboard.Key.alt_gr):
            self.alt_pressed = False

    def start(self):
        self.listener = pynput_keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.daemon = True
        self.listener.start()

    def stop(self):
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass

# ---------------------------------------------------------
# Settings Dialog GUI
# Theme Palette: #DF301C, #FF9100, #FFF1D1, #00B7CD
# ---------------------------------------------------------
def get_ui_asset_path(filename: str) -> str:
    candidates = [
        Path(__file__).parent.parent / filename,
        Path(getattr(sys, '_MEIPASS', '')) / filename if getattr(sys, 'frozen', False) else None,
        Path(sys.executable).parent / filename if getattr(sys, 'frozen', False) else None,
    ]
    for p in candidates:
        if p and p.exists():
            return p.resolve().as_posix()
    return filename

class SettingsDialog(QDialog):
    def __init__(self, config_mgr: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_mgr = config_mgr
        self.setWindowTitle("Diktat - Ayarlar")
        self.setFixedSize(600, 740)

        check_path = get_ui_asset_path("icon_check.png")
        chevron_path = get_ui_asset_path("icon_chevron.png")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: #0c121e;
                color: #FFF1D1;
                font-family: 'Segoe UI', 'Segoe UI Variable', sans-serif;
            }}
            QLabel {{
                color: #FFF1D1;
                font-size: 12px;
                font-weight: 500;
            }}
            QLineEdit, QComboBox {{
                background-color: #080d17;
                color: #FFF1D1;
                border: 1px solid #23334e;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                min-height: 20px;
                selection-background-color: #00B7CD;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid #00B7CD;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border-left: 1px solid #1c2a42;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QComboBox::down-arrow {{
                image: url("{chevron_path}");
                width: 11px;
                height: 11px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #0c121e;
                color: #FFF1D1;
                selection-background-color: #DF301C;
                selection-color: #FFF1D1;
                border: 1px solid #00B7CD;
                padding: 6px;
                outline: none;
            }}
            QCheckBox {{
                color: #FFF1D1;
                font-size: 12px;
                spacing: 11px;
                padding: 4px 0px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1.5px solid #334a6d;
                border-radius: 4px;
                background-color: #080d17;
            }}
            QCheckBox::indicator:hover {{
                border: 1.5px solid #00B7CD;
            }}
            QCheckBox::indicator:checked {{
                background-color: #00B7CD;
                border: 1.5px solid #00B7CD;
                image: url("{check_path}");
            }}
            QGroupBox {{
                background-color: #0e1524;
                border: 1px solid #1c2a42;
                border-radius: 10px;
                margin-top: 18px;
                font-weight: bold;
                color: #FF9100;
                font-size: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 14px;
                padding: 0 6px;
                background-color: #0c121e;
                color: #FF9100;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 20)
        layout.setSpacing(14)

        # 1. API & Model Settings
        api_group = QGroupBox("Yapay Zeka Modeli")
        api_layout = QVBoxLayout(api_group)
        api_layout.setContentsMargins(16, 22, 16, 16)
        api_layout.setSpacing(10)

        api_layout.addWidget(QLabel("Model Sağlayıcı:"))
        self.combo_provider = QComboBox()
        self.combo_provider.addItems([
            "⚡ Yerel AI (RTX 4060 Ti: Faster-Whisper + Qwen) - Çevrimdışı",
            "✨ Google Gemini 3.7 Flash (Bulut)",
            "🌐 OpenAI Whisper + GPT-4o-mini (Bulut)"
        ])
        p = self.config_mgr.get("provider", "local")
        if p == "local":
            self.combo_provider.setCurrentIndex(0)
        elif p == "gemini":
            self.combo_provider.setCurrentIndex(1)
        elif p == "openai":
            self.combo_provider.setCurrentIndex(2)
        api_layout.addWidget(self.combo_provider)

        # Local LLM Model Selector for A/B Testing
        self.lbl_local_model = QLabel("Yerel Düzeltme Modeli:")
        api_layout.addWidget(self.lbl_local_model)
        self.combo_local_model = QComboBox()
        self.combo_local_model.addItems([
            "⚡ Google Gemma 3 4B Instruct (4-bit Q4_K_M) - Disiplinli & Doğru (Önerilen)",
            "⚡ Qwen 2.5 3B Instruct (4-bit Q4_K_M) - Hafif & Hızlı",
            "🚀 Qwen3 4B Instruct 2507 (4-bit Q4_K_M) - Yüksek Kapasite"
        ])
        current_model = self.config_mgr.get("local_llm_model", "gemma-3-4b")
        if current_model == "gemma-3-4b":
            self.combo_local_model.setCurrentIndex(0)
        elif current_model == "qwen2.5-3b":
            self.combo_local_model.setCurrentIndex(1)
        elif current_model == "qwen3-4b":
            self.combo_local_model.setCurrentIndex(2)
        else:
            self.combo_local_model.setCurrentIndex(0)
        api_layout.addWidget(self.combo_local_model)

        self.lbl_gemini = QLabel("Gemini API Anahtarı (Bulut Modu İçin):")
        api_layout.addWidget(self.lbl_gemini)
        self.txt_gemini = QLineEdit(self.config_mgr.get("gemini_api_key", ""))
        self.txt_gemini.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_gemini.setPlaceholderText("Yerel AI modunda anahtar gerekmez...")
        api_layout.addWidget(self.txt_gemini)

        self.lbl_local_status = QLabel("⚡ RTX 4060 Ti GPU (CUDA) devrede: %100 Çevrimdışı ve Limitsiz.")
        self.lbl_local_status.setStyleSheet("color: #00B7CD; font-size: 11px; font-weight: 500;")
        api_layout.addWidget(self.lbl_local_status)

        self.combo_provider.currentIndexChanged.connect(self._on_provider_changed)
        self._on_provider_changed(self.combo_provider.currentIndex())

        layout.addWidget(api_group)

        # 2. General Preferences
        gen_group = QGroupBox("Diktat Tercihleri")
        gen_layout = QVBoxLayout(gen_group)
        gen_layout.setContentsMargins(16, 22, 16, 16)
        gen_layout.setSpacing(12)

        # Shortcut row
        hk_row = QHBoxLayout()
        hk_row.addWidget(QLabel("Global Kısayol:"))
        lbl_hk = QLabel("Ctrl + Space")
        lbl_hk.setStyleSheet("""
            color: #00B7CD;
            background-color: #080d17;
            border: 1px solid #1c2a42;
            border-radius: 6px;
            padding: 3px 12px;
            font-weight: bold;
            font-family: Consolas, monospace;
            font-size: 13px;
        """)
        hk_row.addWidget(lbl_hk)
        hk_row.addStretch()
        gen_layout.addLayout(hk_row)

        # Two-column layout for Language and Overlay Corner with plenty of room
        select_row = QHBoxLayout()
        select_row.setSpacing(16)

        # Left Column: Language
        col_lang = QVBoxLayout()
        col_lang.setSpacing(6)
        col_lang.addWidget(QLabel("Konuşma Dili:"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["Türkçe (tr)", "English (en)", "Otomatik (auto)"])
        l = self.config_mgr.get("language", "tr")
        if l == "en":
            self.combo_lang.setCurrentIndex(1)
        elif l == "auto":
            self.combo_lang.setCurrentIndex(2)
        else:
            self.combo_lang.setCurrentIndex(0)
        col_lang.addWidget(self.combo_lang)
        select_row.addLayout(col_lang)

        # Right Column: Indicator Position
        col_corner = QVBoxLayout()
        col_corner.setSpacing(6)
        col_corner.addWidget(QLabel("Gösterge Konumu:"))
        self.combo_corner = QComboBox()
        self.combo_corner.addItems([
            "Sağ Alt Köşe (Önerilen)",
            "Sol Alt Köşe",
            "Sağ Üst Köşe",
            "Sol Üst Köşe"
        ])
        c = self.config_mgr.get("overlay_corner", "bottom-right")
        corners = ["bottom-right", "bottom-left", "top-right", "top-left"]
        if c in corners:
            self.combo_corner.setCurrentIndex(corners.index(c))
        col_corner.addWidget(self.combo_corner)
        select_row.addLayout(col_corner)

        gen_layout.addLayout(select_row)

        # Distinct spacing between comboboxes and checkboxes
        gen_layout.addSpacing(16)

        # Checkboxes
        self.chk_autostart = QCheckBox("Windows başlangıcında otomatik başlat (Arka planda)")
        autostart_active = is_autostart_enabled() or self.config_mgr.get("auto_start", False)
        self.chk_autostart.setChecked(autostart_active)
        gen_layout.addWidget(self.chk_autostart)

        self.chk_auto_paste = QCheckBox("Metni otomatik olarak imlecin olduğu yere yapıştır (Ctrl+V)")
        self.chk_auto_paste.setChecked(self.config_mgr.get("auto_paste", True))
        gen_layout.addWidget(self.chk_auto_paste)

        self.chk_cleanup = QCheckBox("Akıllı temizlemeyi etkinleştir (ıı, şey seslerini sil, noktalama ekle)")
        self.chk_cleanup.setChecked(self.config_mgr.get("cleanup_enabled", True))
        gen_layout.addWidget(self.chk_cleanup)

        self.chk_sound = QCheckBox("Kayıt başlangıç/bitiş sesli uyarısını çal (Bip sesi)")
        self.chk_sound.setChecked(self.config_mgr.get("play_sound", True))
        gen_layout.addWidget(self.chk_sound)

        layout.addWidget(gen_group)

        # 3. Glossary
        dict_group = QGroupBox("Özel İsimler && Terimler Sözlüğü")
        dict_layout = QVBoxLayout(dict_group)
        dict_layout.setContentsMargins(16, 22, 16, 16)
        dict_layout.setSpacing(8)
        self.txt_glossary = QLineEdit(self.config_mgr.get("glossary", ""))
        self.txt_glossary.setPlaceholderText("Kubernetes, Grafana, PyQt, Claude, Gemini...")
        dict_layout.addWidget(self.txt_glossary)
        layout.addWidget(dict_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1a2538;
                color: #FFF1D1;
                border: 1px solid #2d3e5b;
                border-radius: 8px;
                padding: 9px 20px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #27374e;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Kaydet")
        btn_save.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #DF301C, stop:1 #FF9100);
                color: #FFF1D1;
                border: none;
                border-radius: 8px;
                padding: 9px 28px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f03e29, stop:1 #ffa31a);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #c82513, stop:1 #e68200);
            }
        """)
        btn_save.clicked.connect(self.save_and_close)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def save_and_close(self):
        self.config_mgr.set("gemini_api_key", self.txt_gemini.text().strip())
        providers = ["local", "gemini", "openai"]
        chosen_provider = providers[self.combo_provider.currentIndex()]
        self.config_mgr.set("provider", chosen_provider)
        
        langs = ["tr", "en", "auto"]
        self.config_mgr.set("language", langs[self.combo_lang.currentIndex()])

        # Save selected Local LLM Model (A/B Test)
        model_keys = ["gemma-3-4b", "qwen2.5-3b", "qwen3-4b"]
        idx = max(0, min(len(model_keys) - 1, self.combo_local_model.currentIndex()))
        chosen_local_model = model_keys[idx]
        old_local_model = self.config_mgr.get("local_llm_model", "gemma-3-4b")
        self.config_mgr.set("local_llm_model", chosen_local_model)
        
        # If local model changed, reload in background
        if chosen_local_model != old_local_model and chosen_provider == "local":
            try:
                from .local_engine import LocalAIEngine
                threading.Thread(target=lambda: LocalAIEngine.get_instance().reload_llm(chosen_local_model), daemon=True).start()
            except Exception as e:
                print(f"Error reloading local LLM: {e}")

        corners = ["bottom-right", "bottom-left", "top-right", "top-left"]
        self.config_mgr.set("overlay_corner", corners[self.combo_corner.currentIndex()])

        # Update autostart
        enable_autostart = self.chk_autostart.isChecked()
        self.config_mgr.set("auto_start", enable_autostart)
        set_autostart(enable_autostart)

        self.config_mgr.set("auto_paste", self.chk_auto_paste.isChecked())
        self.config_mgr.set("cleanup_enabled", self.chk_cleanup.isChecked())
        self.config_mgr.set("play_sound", self.chk_sound.isChecked())
        self.config_mgr.set("glossary", self.txt_glossary.text().strip())
        self.accept()

    def _on_provider_changed(self, index: int):
        is_local = (index == 0)
        is_gemini = (index == 1)

        self.lbl_local_model.setVisible(is_local)
        self.combo_local_model.setVisible(is_local)
        self.lbl_local_status.setVisible(is_local)

        self.lbl_gemini.setVisible(is_gemini)
        self.txt_gemini.setVisible(is_gemini)

# ---------------------------------------------------------
# Main Diktat Background Controller
# ---------------------------------------------------------
class DiktatApplication:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.config_mgr = ConfigManager()
        self.signals = AppSignals()
        self.recorder = AudioRecorder(sample_rate=self.config_mgr.get("sample_rate", 16000))
        self.ai_client = AIClient(self.config_mgr.config)

        # Preload local models in background if provider is local
        if self.config_mgr.get("provider", "local") == "local":
            from .local_engine import LocalAIEngine
            LocalAIEngine.get_instance(self.config_mgr.config).preload_in_background()

        self.hud = FloatingHUD(self.config_mgr)

        self.is_recording = False
        self.is_processing = False
        self.elapsed_sec = 0

        # Synchronize autostart registry if enabled in config
        if self.config_mgr.get("auto_start", False):
            set_autostart(True)

        self.setup_signals()
        self.setup_tray()

        # Start Global Key Listener
        self.key_listener = GlobalKeyListener(self.signals)
        self.key_listener.start()

        # Audio level timer
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.on_poll_audio)
        self.poll_timer.start(80)

        # Seconds tick timer
        self.sec_timer = QTimer()
        self.sec_timer.timeout.connect(self.on_second_tick)

        prov = self.config_mgr.get("provider", "local")
        engine_label = "Yerel GPU (RTX 4060 Ti)" if prov == "local" else "Bulut AI"
        self.tray.showMessage(
            "Diktat Hazır",
            f"Diktat arka planda hazır ({engine_label}). İstediğiniz yazı alanında Ctrl + Space tuşlarına basarak dikte edin.",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    def setup_signals(self):
        self.signals.toggle_requested.connect(self.toggle_recording)
        self.signals.cancel_requested.connect(self.cancel_recording)
        self.signals.status_changed.connect(self.hud.set_state)
        self.signals.level_updated.connect(self.hud.set_db)
        self.signals.text_processed.connect(self._on_text_ready)
        self.signals.error_occurred.connect(self._on_error)

    def setup_tray(self):
        icon = None
        candidates = [
            Path(__file__).parent.parent / "icon.png",
            Path(__file__).parent.parent / "icon.ico",
            Path(getattr(sys, '_MEIPASS', '')) / "icon.png" if getattr(sys, 'frozen', False) else None,
            Path(getattr(sys, '_MEIPASS', '')) / "icon.ico" if getattr(sys, 'frozen', False) else None,
            Path(sys.executable).parent / "icon.png" if getattr(sys, 'frozen', False) else None,
            Path(sys.executable).parent / "icon.ico" if getattr(sys, 'frozen', False) else None,
        ]
        for p in candidates:
            if p and p.exists():
                icon = QIcon(str(p))
                break

        if not icon or icon.isNull():
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(QColor(255, 145, 0))) # #FF9100 Orange
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
            painter.end()
            icon = QIcon(pixmap)

        self.tray = QSystemTrayIcon(icon, self.app)
        self.tray.setToolTip("Diktat - AI Sesli Dikte (Ctrl + Space)")

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #0c121e;
                color: #FFF1D1;
                border: 1px solid #1c2a42;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
            }
            QMenu::item {
                padding: 7px 22px;
                border-radius: 6px;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #DF301C;
                color: #FFF1D1;
            }
            QMenu::separator {
                height: 1px;
                background: #1c2a42;
                margin: 4px 8px;
            }
        """)

        act_toggle = QAction("🎙️ Diktatı Başlat/Durdur (Ctrl+Space)", menu)
        act_toggle.triggered.connect(self.toggle_recording)
        menu.addAction(act_toggle)

        menu.addSeparator()

        act_settings = QAction("⚙️ Ayarlar...", menu)
        act_settings.triggered.connect(self.open_settings)
        menu.addAction(act_settings)

        menu.addSeparator()

        act_quit = QAction("❌ Çıkış", menu)
        act_quit.triggered.connect(self.quit_app)
        menu.addAction(act_quit)

        self.tray.setContextMenu(menu)
        self.tray.show()

    def toggle_recording(self):
        if self.is_processing:
            return
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_and_process()

    def start_recording(self):
        try:
            self.recorder.start()
            self.is_recording = True
            self.elapsed_sec = 0
            self.sec_timer.start(1000)
            self.signals.status_changed.emit("recording", "Dinliyor...")

            if self.config_mgr.get("play_sound", True):
                threading.Thread(target=lambda: winsound.Beep(950, 80), daemon=True).start()
        except Exception as e:
            print(f"Record start error: {e}")
            self.signals.error_occurred.emit(f"Mikrofon hatası: {e}")

    def stop_and_process(self):
        if not self.is_recording:
            return
        self.is_recording = False
        self.sec_timer.stop()
        self.is_processing = True

        if self.config_mgr.get("play_sound", True):
            threading.Thread(target=lambda: winsound.Beep(1200, 80), daemon=True).start()

        self.signals.status_changed.emit("transcribing", "Yazıya çevriliyor...")
        threading.Thread(target=self._process_pipeline_thread, daemon=True).start()

    def cancel_recording(self):
        if self.is_recording:
            self.is_recording = False
            self.sec_timer.stop()
            self.recorder.stop()
            self.signals.status_changed.emit("idle", "")

    def on_second_tick(self):
        if self.is_recording:
            self.elapsed_sec += 1
            self.hud.set_timer(self.elapsed_sec)
            if self.elapsed_sec >= self.config_mgr.get("max_duration_seconds", 300):
                self.stop_and_process()

    def on_poll_audio(self):
        if self.is_recording:
            db = self.recorder.get_current_db()
            self.signals.level_updated.emit(db)

    def _process_pipeline_thread(self):
        try:
            audio_data = self.recorder.stop()
            if len(audio_data) < 1600:
                self.signals.status_changed.emit("idle", "")
                self.is_processing = False
                return

            self.signals.status_changed.emit("transcribing", "Yazıya çevriliyor...")
            raw, cleaned = self.ai_client.transcribe_and_cleanup(
                audio_data,
                sample_rate=self.config_mgr.get("sample_rate", 16000)
            )

            if not cleaned:
                self.signals.status_changed.emit("error", "Ses algılanamadı")
                self.is_processing = False
                return

            self.signals.text_processed.emit(raw, cleaned)
        except Exception as e:
            print(f"Pipeline error: {e}")
            self.signals.error_occurred.emit(str(e))
        finally:
            self.is_processing = False

    def _on_text_ready(self, raw: str, cleaned: str):
        # 1. Copy to clipboard
        pyperclip.copy(cleaned)

        # 2. Auto-Paste directly into currently active cursor
        if self.config_mgr.get("auto_paste", True):
            time.sleep(0.06)
            try:
                windows_paste()
            except Exception as e:
                print(f"Windows paste error: {e}")

        self.signals.status_changed.emit("done", "Yapıştırıldı")

    def _on_error(self, err_msg: str):
        self.signals.status_changed.emit("error", err_msg)

    def open_settings(self):
        dlg = SettingsDialog(self.config_mgr)
        if dlg.exec():
            self.ai_client = AIClient(self.config_mgr.config)
            self.hud.reposition()

    def quit_app(self):
        self.cancel_recording()
        if hasattr(self, 'key_listener') and self.key_listener:
            self.key_listener.stop()
        self.tray.hide()
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec())

# Backward compatibility alias
DikteApplication = DiktatApplication

if __name__ == "__main__":
    app = DiktatApplication()
    app.run()
