import sys
import os
import time
import threading
import math
import ctypes
import winsound
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

from .config import ConfigManager
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

        self.setFixedSize(280, 52)
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
        painter.setBrush(QBrush(QColor(15, 23, 42, 245)))
        painter.setPen(QPen(QColor(51, 65, 85, 220), 1.5))
        painter.drawRoundedRect(bg_rect, 24, 24)

        dot_x = 24
        dot_y = self.height() // 2
        pulse = (math.sin(self.pulse_phase) + 1.0) / 2.0

        if self.state == "recording":
            glow_radius = 7 + pulse * 5
            painter.setBrush(QBrush(QColor(239, 68, 68, int(80 + pulse * 120))))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(dot_x, dot_y), int(glow_radius), int(glow_radius))

            painter.setBrush(QBrush(QColor(239, 68, 68)))
            painter.drawEllipse(QPoint(dot_x, dot_y), 4, 4)

            m = self.elapsed_seconds // 60
            s = self.elapsed_seconds % 60
            time_str = f"{m:02d}:{s:02d}"

            painter.setPen(QPen(QColor(248, 113, 113)))
            painter.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
            painter.drawText(42, dot_y + 4, time_str)

            db_display = f"{self.db_level:.0f} dB" if self.db_level > -85 else "Konuşun..."
            painter.setPen(QPen(QColor(148, 163, 184)))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(98, dot_y + 4, f"• {db_display}")

        elif self.state == "transcribing":
            painter.setBrush(QBrush(QColor(59, 130, 246)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(dot_x, dot_y), 5, 5)

            painter.setPen(QPen(QColor(147, 197, 253)))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.drawText(42, dot_y + 4, "Yazıya çevriliyor...")

        elif self.state == "cleaning":
            painter.setBrush(QBrush(QColor(168, 85, 247)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(dot_x, dot_y), 5, 5)

            painter.setPen(QPen(QColor(216, 180, 254)))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.drawText(42, dot_y + 4, "Metin temizleniyor...")

        elif self.state == "done":
            painter.setBrush(QBrush(QColor(34, 197, 94)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(dot_x, dot_y), 5, 5)

            painter.setPen(QPen(QColor(134, 239, 172)))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(42, dot_y + 4, "✓ Yapıştırıldı")

        elif self.state == "error":
            painter.setBrush(QBrush(QColor(244, 63, 94)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(dot_x, dot_y), 5, 5)

            painter.setPen(QPen(QColor(253, 164, 175)))
            painter.setFont(QFont("Segoe UI", 9))
            disp = (self.status_text[:22] + "..") if len(self.status_text) > 22 else self.status_text
            painter.drawText(42, dot_y + 4, disp)

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
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=2,
                dtype='float32',
                callback=self._audio_callback_stereo,
                blocksize=1024
            )
            self.stream.start()

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
# ---------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, config_mgr: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_mgr = config_mgr
        self.setWindowTitle("Dikte - Ayarlar")
        self.setFixedSize(520, 520)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: #f1f5f9; font-family: 'Segoe UI'; }
            QLabel { color: #cbd5e1; font-size: 12px; font-weight: 500; }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #020617; color: #f8fafc;
                border: 1px solid #334155; border-radius: 8px;
                padding: 6px 10px; font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border: 1px solid #3b82f6; }
            QCheckBox { color: #cbd5e1; font-size: 12px; }
            QPushButton {
                background-color: #2563eb; color: white; border: none;
                border-radius: 8px; padding: 8px 16px; font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QGroupBox {
                border: 1px solid #1e293b; border-radius: 8px;
                margin-top: 12px; padding-top: 14px; font-weight: bold; color: #94a3b8;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 1. API Settings
        api_group = QGroupBox("Yapay Zeka Modeli")
        api_layout = QVBoxLayout(api_group)

        api_layout.addWidget(QLabel("Gemini API Anahtarı:"))
        self.txt_gemini = QLineEdit(self.config_mgr.get("gemini_api_key", ""))
        self.txt_gemini.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(self.txt_gemini)

        prov_row = QHBoxLayout()
        prov_row.addWidget(QLabel("Model:"))
        self.combo_provider = QComboBox()
        self.combo_provider.addItems(["Gemini 3.7 Flash (Dahili & En Hızlı)", "OpenAI Whisper"])
        if self.config_mgr.get("provider") == "openai":
            self.combo_provider.setCurrentIndex(1)
        prov_row.addWidget(self.combo_provider)
        api_layout.addLayout(prov_row)
        layout.addWidget(api_group)

        # 2. General Settings
        gen_group = QGroupBox("Dikte Tercihleri")
        gen_layout = QVBoxLayout(gen_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Global Kısayol:"))
        lbl_hk = QLabel("Ctrl + Space")
        lbl_hk.setStyleSheet("color: #60a5fa; font-weight: bold; font-family: Consolas;")
        row1.addWidget(lbl_hk)
        row1.addStretch()

        row1.addWidget(QLabel("Konuşma Dili:"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["Türkçe (tr)", "English (en)", "Otomatik (auto)"])
        l = self.config_mgr.get("language", "tr")
        if l == "en":
            self.combo_lang.setCurrentIndex(1)
        elif l == "auto":
            self.combo_lang.setCurrentIndex(2)
        row1.addWidget(self.combo_lang)
        gen_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Gösterge Konumu:"))
        self.combo_corner = QComboBox()
        self.combo_corner.addItems(["Sağ Alt (bottom-right)", "Sol Alt (bottom-left)", "Sağ Üst (top-right)", "Sol Üst (top-left)"])
        c = self.config_mgr.get("overlay_corner", "bottom-right")
        corners = ["bottom-right", "bottom-left", "top-right", "top-left"]
        if c in corners:
            self.combo_corner.setCurrentIndex(corners.index(c))
        row2.addWidget(self.combo_corner)
        gen_layout.addLayout(row2)

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
        dict_group = QGroupBox("Özel İsimler & Terimler Sözlüğü")
        dict_layout = QVBoxLayout(dict_group)
        self.txt_glossary = QLineEdit(self.config_mgr.get("glossary", ""))
        self.txt_glossary.setPlaceholderText("Kubernetes, Grafana, PyQt, Claude...")
        dict_layout.addWidget(self.txt_glossary)
        layout.addWidget(dict_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Kaydet")
        btn_save.clicked.connect(self.save_and_close)
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background-color: #334155;")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def save_and_close(self):
        self.config_mgr.set("gemini_api_key", self.txt_gemini.text().strip())
        self.config_mgr.set("provider", "openai" if self.combo_provider.currentIndex() == 1 else "gemini")
        
        langs = ["tr", "en", "auto"]
        self.config_mgr.set("language", langs[self.combo_lang.currentIndex()])

        corners = ["bottom-right", "bottom-left", "top-right", "top-left"]
        self.config_mgr.set("overlay_corner", corners[self.combo_corner.currentIndex()])

        self.config_mgr.set("auto_paste", self.chk_auto_paste.isChecked())
        self.config_mgr.set("cleanup_enabled", self.chk_cleanup.isChecked())
        self.config_mgr.set("play_sound", self.chk_sound.isChecked())
        self.config_mgr.set("glossary", self.txt_glossary.text().strip())
        self.accept()

# ---------------------------------------------------------
# Main Dikte Background Controller
# ---------------------------------------------------------
class DikteApplication:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.config_mgr = ConfigManager()
        self.signals = AppSignals()
        self.recorder = AudioRecorder(sample_rate=self.config_mgr.get("sample_rate", 16000))
        self.ai_client = AIClient(self.config_mgr.config)

        self.hud = FloatingHUD(self.config_mgr)

        self.is_recording = False
        self.is_processing = False
        self.elapsed_sec = 0

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

        # Show desktop notification that Dikte is ready
        self.tray.showMessage(
            "Dikte Hazır",
            "Dikte arka planda hazır. İstediğiniz yazı alanında Ctrl + Space tuşlarına basarak dikte edin.",
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
        icon_path = os.path.join(os.path.dirname(__file__), "..", "icon.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(__file__), "..", "icon.ico")

        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(QColor(37, 99, 235)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
            painter.end()
            icon = QIcon(pixmap)

        self.tray = QSystemTrayIcon(icon, self.app)
        self.tray.setToolTip("Dikte - AI Sesli Dikte (Ctrl + Space)")

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #0f172a; color: #f1f5f9; border: 1px solid #334155; padding: 6px; font-family: 'Segoe UI'; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #2563eb; }
        """)

        act_toggle = QAction("🎙️ Dikteyi Başlat/Durdur (Ctrl+Space)", menu)
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

if __name__ == "__main__":
    app = DikteApplication()
    app.run()
