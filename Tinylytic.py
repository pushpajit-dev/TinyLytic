"""
TinyLytic - Studio AI
Universal Speech Transcription, Realtime Recording, Vision OCR & AI Chat Studio
Version: 3.1
Copyright (c) 2025 Aivory Products
"""

import sys
import os
import glob
import json
import time
import tempfile
import subprocess
import platform
import warnings
import re

# Suppress PyTorch CUDA toolkit and JIT compiler warnings
os.environ["CUDA_MODULE_LOADING"] = "LAZY"
os.environ["TORCH_CPP_LOG_LEVEL"] = "ERROR"
warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", message=".*CUDA toolkit not found.*")

# Graceful pyperclip fallback
try:
    import pyperclip
except ImportError:
    class SafeClipboard:
        @staticmethod
        def copy(text):
            try:
                import tkinter as tk
                r = tk.Tk()
                r.withdraw()
                r.clipboard_clear()
                r.clipboard_append(text)
                r.update()
                r.destroy()
            except Exception:
                pass

        @staticmethod
        def paste():
            try:
                import tkinter as tk
                r = tk.Tk()
                r.withdraw()
                val = r.clipboard_get()
                r.destroy()
                return val
            except Exception:
                return ""
    pyperclip = SafeClipboard()

# Graceful requests fallback
try:
    import requests
except ImportError:
    requests = None

# PyQt6 check with auto-recovery notice
try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QTextEdit, QProgressBar, QFileDialog,
        QTabWidget, QToolBar, QMainWindow, QMenu, QMenuBar, QMessageBox,
        QGroupBox, QFormLayout, QDialog, QComboBox, QSplitter, QFrame,
        QCheckBox, QSpinBox, QStatusBar, QScrollArea
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
    from PyQt6.QtGui import QFont, QIcon, QColor, QPalette, QTextCursor
except ImportError:
    print("\n" + "=" * 65)
    print(" [!] Missing Dependency: PyQt6 is not installed in this Python environment.")
    print(" Please run: pip install PyQt6 pyperclip openai-whisper sounddevice soundfile")
    print(" Or double-click 'test_and_run.bat' to automatically install all dependencies.")
    print("=" * 65 + "\n")
    input("Press Enter to exit...")
    sys.exit(1)

import ctypes

def get_console_hwnd():
    """Retrieve Windows console window handle."""
    try:
        return ctypes.windll.kernel32.GetConsoleWindow()
    except Exception:
        return 0

def hide_console():
    """Hide the background Windows command terminal."""
    hwnd = get_console_hwnd()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE

def show_console():
    """Show the Windows command terminal."""
    hwnd = get_console_hwnd()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
        ctypes.windll.user32.SetForegroundWindow(hwnd)

def is_console_visible():
    """Check if the Windows command terminal is currently visible."""
    hwnd = get_console_hwnd()
    if hwnd:
        return bool(ctypes.windll.user32.IsWindowVisible(hwnd))
    return False

class StreamRedirector(QObject):
    """Safely stream stdout and stderr to the graphical Settings log widget."""
    text_written = pyqtSignal(str)

    def __init__(self, original_stream):
        super().__init__()
        self.original_stream = original_stream

    def write(self, text):
        if self.original_stream:
            try:
                self.original_stream.write(text)
            except Exception:
                pass
        if text:
            self.text_written.emit(text)

    def flush(self):
        if self.original_stream:
            try:
                self.original_stream.flush()
            except Exception:
                pass

from core_engine import (
    BASE_DIR, TEMP_DIR, setup_ffmpeg, resource_path,
    get_system_specs, get_available_whisper_models,
    SUPPORTED_LANGUAGES, format_seconds, export_transcript,
    WHISPER_DOWNLOAD_CATALOG, clean_transcript_text, get_app_data_dir
)

def get_license_file_path():
    """Return persistent license.json path in LocalAppData."""
    try:
        base_dir = get_app_data_dir()
    except Exception:
        base_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "TinyLytic")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "license.json")
from workers import (
    UnifiedTranscriptionWorker, YouTubeDownloadWorker,
    RealtimeRecorderWorker, VisionAnalysisWorker, ChatWorker,
    ModelDownloadWorker, CudaInstallWorker, PackageUpdateWorker
)
from chat_engine import AIChatManager, HAS_LLAMA
from vision_engine import HAS_CV2, HAS_PYTESSERACT

# Safe sounddevice query for input devices
try:
    import sounddevice as sd
    HAS_SD = True
except Exception:
    HAS_SD = False
    sd = None


# Modern Clean Dark Theme Stylesheet (Pure White Text on Buttons, No Emojis)
MODERN_STYLESHEET = """
QMainWindow {
    background-color: #12141a;
}
QWidget {
    color: #e2e8f0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 10pt;
}
QTabWidget::pane {
    border: 1px solid #2d3748;
    background-color: #1a1e29;
    border-radius: 8px;
    padding: 10px;
}
QTabBar::tab {
    background-color: #161a23;
    color: #a0aec0;
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #2b354f;
    color: #63b3ed;
    border-bottom: 2px solid #3182ce;
}
QTabBar::tab:hover {
    background-color: #232a3b;
    color: #cbd5e0;
}
QGroupBox {
    border: 1px solid #2d3748;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 16px;
    font-weight: bold;
    color: #63b3ed;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
}
QPushButton {
    background-color: #2b6cb0;
    color: #ffffff;
    border: none;
    padding: 9px 18px;
    border-radius: 6px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #3182ce;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #2c5282;
    color: #ffffff;
}
QPushButton:disabled {
    background-color: #2d3748;
    color: #718096;
}
QPushButton#actionBtn {
    background-color: #319795;
    color: #ffffff;
}
QPushButton#actionBtn:hover {
    background-color: #38b2ac;
    color: #ffffff;
}
QPushButton#dangerBtn {
    background-color: #c53030;
    color: #ffffff;
}
QPushButton#dangerBtn:hover {
    background-color: #e53e3e;
    color: #ffffff;
}
QPushButton#recordBtn {
    background-color: #d9383a;
    color: #ffffff;
    font-size: 11pt;
    font-weight: bold;
    padding: 10px 24px;
    border-radius: 6px;
}
QPushButton#recordBtn:hover {
    background-color: #e53e3e;
    color: #ffffff;
}
QPushButton#transcribeBtn {
    background-color: #2b6cb0;
    color: #ffffff;
    font-size: 11pt;
    font-weight: bold;
    padding: 10px 24px;
    border-radius: 6px;
}
QPushButton#transcribeBtn:hover {
    background-color: #3182ce;
    color: #ffffff;
}
QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: #12151e;
    border: 1px solid #2d3748;
    border-radius: 6px;
    padding: 8px;
    color: #f7fafc;
    font-family: "Segoe UI", "Nirmala UI", "Vrinda", "Kalpurush", sans-serif;
    selection-background-color: #3182ce;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #63b3ed;
}
QProgressBar {
    border: 1px solid #2d3748;
    border-radius: 5px;
    text-align: center;
    background-color: #12151e;
    color: #ffffff;
    height: 18px;
}
QProgressBar::chunk {
    background-color: #3182ce;
    border-radius: 4px;
}
QMenuBar {
    background-color: #161a23;
    color: #e2e8f0;
    border-bottom: 1px solid #2d3748;
}
QMenuBar::item:selected {
    background-color: #2b354f;
    border-radius: 4px;
}
QMenu {
    background-color: #1a1e29;
    color: #e2e8f0;
    border: 1px solid #2d3748;
}
QMenu::item:selected {
    background-color: #3182ce;
}
QStatusBar {
    background-color: #161a23;
    color: #a0aec0;
    border-top: 1px solid #2d3748;
}
"""

class TinyLyticApp(QMainWindow):
    """Flagship Unified TinyLytic Application."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TinyLytic - Studio AI")
        self.setGeometry(80, 60, 1100, 780)
        self.setMinimumSize(850, 600)

        # Hide Windows command prompt window by default
        hide_console()

        # Set App Icon
        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Core State
        self.chat_manager = AIChatManager()
        self.current_transcript_segments = []
        self.current_transcript_text = ""
        self.is_recording = False
        self.recorder_worker = None
        self.active_worker = None

        # Activation status
        self.activated_key = ""
        self.is_activated = self.checkInitialActivation()

        # Build UI
        self.initMenuBar()
        self.initStatusBar()
        self.initMainLayout()

        # Apply activation state across tabs and banners
        self.applyActivationState()

        # Apply Modern Theme
        self.setStyleSheet(MODERN_STYLESHEET)

        # Redirect standard streams to GUI terminal
        self.stdout_redirector = StreamRedirector(sys.stdout)
        self.stdout_redirector.text_written.connect(self.appendTerminalLog)
        sys.stdout = self.stdout_redirector

        self.stderr_redirector = StreamRedirector(sys.stderr)
        self.stderr_redirector.text_written.connect(self.appendTerminalLog)
        sys.stderr = self.stderr_redirector

        # Start periodic resource monitor
        self.initResourceTimer()

    def checkInitialActivation(self):
        """Check persistent license in AppData and local activated.flag."""
        self.activated_key = ""
        # 1. Check license.json in AppData
        try:
            lic_file = get_license_file_path()
            if os.path.exists(lic_file):
                with open(lic_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("activated") is True:
                        self.activated_key = data.get("license_key", "")
                        return True
        except Exception:
            pass

        # 2. Check local activated.flag
        flag_path = resource_path("activated.flag")
        if os.path.exists(flag_path):
            try:
                with open(flag_path, "r", encoding="utf-8") as f:
                    if "true" in f.read().lower():
                        key_file = resource_path("Activation Key.txt")
                        if os.path.exists(key_file):
                            try:
                                with open(key_file, "r", encoding="utf-8") as kf:
                                    self.activated_key = kf.read().strip().upper()
                            except Exception:
                                pass
                        if not self.activated_key:
                            self.activated_key = "6F0E4C97-B72A4E69-A11BF6C4-AF6517E7"
                        return True
            except Exception:
                pass
        return False

    def initMenuBar(self):
        menu = self.menuBar()

        # File Menu
        file_menu = menu.addMenu("File")
        file_menu.addAction("Save Session", self.saveSession)
        file_menu.addAction("Load Session", self.loadSession)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        # Export Menu
        export_menu = menu.addMenu("Export")
        export_menu.addAction("Export as TXT (Chapter Timestamps)", lambda: self.exportCurrent("txt"))
        export_menu.addAction("Export as TXT (Clean Text)", lambda: self.exportCurrent("clean"))
        export_menu.addAction("Export as JSON (.json)", lambda: self.exportCurrent("json"))
        export_menu.addAction("Export as SRT (.srt)", lambda: self.exportCurrent("srt"))
        export_menu.addAction("Export as VTT (.vtt)", lambda: self.exportCurrent("vtt"))
        export_menu.addAction("Export as CSV (.csv)", lambda: self.exportCurrent("csv"))

        # Tools Menu
        tools_menu = menu.addMenu("Tools")
        tools_menu.addAction("Clear", self.clearTempCache)
        tools_menu.addAction("Clean Transcript", self.cleanCurrentTranscript)
        tools_menu.addAction("Benchmark", self.switchToSettingsTab)

        # Help Menu
        help_menu = menu.addMenu("Help")
        help_menu.addAction("Activation", self.showActivationDialog)
        help_menu.addAction("Help", self.showAboutDialog)

    def initStatusBar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label, 1)

        self.resource_label = QLabel("CPU: --% | RAM: --%")
        self.resource_label.setStyleSheet("color: #63b3ed; padding-right: 15px; font-weight: bold;")
        self.status_bar.addPermanentWidget(self.resource_label)

    def initResourceTimer(self):
        self.res_timer = QTimer(self)
        self.res_timer.timeout.connect(self.updateResourceUsage)
        self.res_timer.start(2500)

    def updateResourceUsage(self):
        try:
            import psutil
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            self.resource_label.setText(f"CPU: {cpu:.0f}% | RAM: {ram:.0f}%")
        except Exception:
            pass

    def initMainLayout(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 5)

        # Global Settings Header
        header_group = QGroupBox("Model & Speech Settings")
        header_layout = QHBoxLayout(header_group)

        # Model Selector
        header_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        models = get_available_whisper_models()
        for m in models:
            self.model_combo.addItem(m["name"], m["id"])
        self.model_combo.setCurrentIndex(0)
        header_layout.addWidget(self.model_combo)

        # Language Selector
        header_layout.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        for name, code in SUPPORTED_LANGUAGES.items():
            self.lang_combo.addItem(name, code)
        self.lang_combo.setCurrentIndex(0)
        header_layout.addWidget(self.lang_combo)

        # Task Selector (Transcribe vs Translate)
        header_layout.addWidget(QLabel("Task:"))
        self.task_combo = QComboBox()
        self.task_combo.addItem("Transcribe", "transcribe")
        self.task_combo.addItem("Translate", "translate")
        header_layout.addWidget(self.task_combo)

        # Chapter Chunk Length
        header_layout.addWidget(QLabel("Chunk:"))
        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(30, 300)
        self.chunk_spin.setValue(100)
        self.chunk_spin.setSuffix(" chars")
        header_layout.addWidget(self.chunk_spin)

        # Multi-Speaker Diarization Controls
        self.multi_speaker_check = QCheckBox("Multi-Speaker")
        self.multi_speaker_check.setChecked(True)
        self.multi_speaker_check.setStyleSheet("font-weight: bold; color: #63b3ed;")
        header_layout.addWidget(self.multi_speaker_check)

        self.speaker_count_spin = QSpinBox()
        self.speaker_count_spin.setRange(0, 6)
        self.speaker_count_spin.setValue(0)
        self.speaker_count_spin.setSpecialValueText("Auto Detect")
        self.speaker_count_spin.setSuffix(" Speakers")
        header_layout.addWidget(self.speaker_count_spin)

        main_layout.addWidget(header_group)

        # Main Tabs Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, 1)

        # 1. Chat Tab
        self.tab_chat = self.createChatTab()
        self.tabs.addTab(self.tab_chat, "Chat" if self.is_activated else "Chat [Pro]")

        # 2. YouTube Tab
        self.tab_youtube = self.createYouTubeTab()
        self.tabs.addTab(self.tab_youtube, "YouTube")

        # 3. Realtime Studio Tab
        self.tab_realtime = self.createRealtimeTab()
        self.tabs.addTab(self.tab_realtime, "Realtime Studio" if self.is_activated else "Realtime Studio [Pro]")

        # 4. Audio Tab
        self.tab_audio = self.createAudioTab()
        self.tabs.addTab(self.tab_audio, "Audio" if self.is_activated else "Audio [Pro]")

        # 5. Video Tab
        self.tab_video = self.createVideoTab()
        self.tabs.addTab(self.tab_video, "Video" if self.is_activated else "Video [Pro]")

        # 6. OCR and Vision Tab
        self.tab_vision = self.createVisionTab()
        self.tabs.addTab(self.tab_vision, "OCR and Vision" if self.is_activated else "OCR and Vision [Pro]")

        # 7. Settings Tab
        self.tab_settings = self.createSettingsTab()
        self.tabs.addTab(self.tab_settings, "Settings")

    def createLockBanner(self, feature_name):
        """Create a clean lock banner for Pro features."""
        banner = QFrame()
        banner.setObjectName("lockBanner")
        banner.setStyleSheet("""
            QFrame#lockBanner {
                background-color: #2d1515;
                border: 1px solid #e53e3e;
                border-radius: 6px;
                padding: 6px 12px;
                margin-bottom: 8px;
            }
        """)
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(10, 5, 10, 5)

        icon_lbl = QLabel("[LOCKED]")
        icon_lbl.setStyleSheet("color: #fc8181; font-weight: bold; font-size: 10pt;")
        layout.addWidget(icon_lbl)

        msg_lbl = QLabel(f"<b>{feature_name}</b> requires TinyLytic Pro activation. YouTube Transcription is 100% free.")
        msg_lbl.setStyleSheet("color: #fed7d7; font-size: 9pt;")
        layout.addWidget(msg_lbl, 1)

        btn_act = QPushButton("Activate Pro")
        btn_act.setStyleSheet("""
            QPushButton {
                background-color: #e53e3e;
                color: #ffffff;
                font-weight: bold;
                padding: 4px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c53030;
            }
        """)
        btn_act.clicked.connect(self.showActivationDialog)
        layout.addWidget(btn_act)

        return banner

    def applyActivationState(self):
        """Synchronize UI with current activation status (Pro lockout vs Unlocked)."""
        is_act = getattr(self, 'is_activated', False)

        # 1. Update tab titles
        if hasattr(self, 'tabs') and self.tabs:
            tab_titles = [
                ("Chat", is_act),
                ("YouTube", True),  # Always free
                ("Realtime Studio", is_act),
                ("Audio", is_act),
                ("Video", is_act),
                ("OCR and Vision", is_act),
                ("Settings", True)
            ]
            for idx, (base_name, active) in enumerate(tab_titles):
                if idx < self.tabs.count():
                    title = base_name if active else f"{base_name} [Pro]"
                    self.tabs.setTabText(idx, title)

        # 2. Update lock banners
        for banner_attr in ['lock_banner_chat', 'lock_banner_realtime', 'lock_banner_audio', 'lock_banner_video', 'lock_banner_vision']:
            if hasattr(self, banner_attr):
                getattr(self, banner_attr).setVisible(not is_act)

        # 3. Enable or disable action controls on locked tabs
        if hasattr(self, 'chat_input'):
            self.chat_input.setEnabled(is_act)
            if not is_act:
                self.chat_input.setPlaceholderText("Activation required to use AI Chat. Please activate TinyLytic Pro...")
            else:
                self.chat_input.setPlaceholderText("Type a message...")
        if hasattr(self, 'chat_send_btn'):
            self.chat_send_btn.setEnabled(is_act)

        if hasattr(self, 'live_record_btn'):
            self.live_record_btn.setEnabled(is_act)
        if hasattr(self, 'live_process_btn'):
            self.live_process_btn.setEnabled(is_act and bool(getattr(self, 'recorded_wav_path', None)))

        if hasattr(self, 'audio_transcribe_btn'):
            self.audio_transcribe_btn.setEnabled(is_act)

        if hasattr(self, 'video_transcribe_btn'):
            self.video_transcribe_btn.setEnabled(is_act)
        if hasattr(self, 'btn_caption_studio'):
            self.btn_caption_studio.setEnabled(is_act)

        if hasattr(self, 'btn_run_slides'):
            self.btn_run_slides.setEnabled(is_act)
        if hasattr(self, 'btn_ocr'):
            self.btn_ocr.setEnabled(is_act)

    def updateTabTitlesForActivation(self):
        """Update tab titles and lock states across the app."""
        self.applyActivationState()

    # =========================================================================
    # TAB 1: CHAT
    # =========================================================================
    def createChatTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.lock_banner_chat = self.createLockBanner("AI Chat Assistant")
        layout.addWidget(self.lock_banner_chat)

        # Quick Action Buttons Row
        quick_row = QHBoxLayout()
        quick_label = QLabel("Quick Actions:")
        quick_label.setStyleSheet("font-weight: bold; color: #63b3ed;")
        quick_row.addWidget(quick_label)

        btn_sum = QPushButton("Summarize")
        btn_sum.clicked.connect(lambda: self.sendChatQuickQuery("Summarize the loaded transcript"))
        quick_row.addWidget(btn_sum)

        btn_chap = QPushButton("Chapters")
        btn_chap.clicked.connect(lambda: self.sendChatQuickQuery("Generate YouTube timestamps and chapter titles"))
        quick_row.addWidget(btn_chap)

        btn_key = QPushButton("Key Points")
        btn_key.clicked.connect(lambda: self.sendChatQuickQuery("Extract key takeaways and action items"))
        quick_row.addWidget(btn_key)

        btn_tone = QPushButton("Tone")
        btn_tone.clicked.connect(lambda: self.sendChatQuickQuery("Analyze the tone and sentiment"))
        quick_row.addWidget(btn_tone)

        quick_row.addStretch()

        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clearChat)
        quick_row.addWidget(btn_clear)

        layout.addLayout(quick_row)

        # Chat Conversation Display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #0f1219; font-size: 10pt; line-height: 1.5; padding: 10px;")
        layout.addWidget(self.chat_display, 1)

        # Clean Initial Welcome Message
        welcome_html = (
            "<div style='color: #63b3ed; font-size: 11pt; font-weight: bold;'>TinyLytic Chat</div>"
            "<p style='color: #a0aec0; margin-top: 4px;'>"
            "You can chat freely here, ask questions, or summarize and analyze transcripts."
            "</p><hr style='border: 0.5px solid #2d3748;'>"
        )
        self.chat_display.setHtml(welcome_html)

        # Chat Input Row
        input_row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type a message...")
        self.chat_input.returnPressed.connect(self.handleSendChat)
        input_row.addWidget(self.chat_input, 1)

        self.chat_send_btn = QPushButton("Send")
        self.chat_send_btn.clicked.connect(self.handleSendChat)
        input_row.addWidget(self.chat_send_btn)

        layout.addLayout(input_row)

        # Model Backend Selection Row
        backend_row = QHBoxLayout()
        backend_row.addWidget(QLabel("Chat Model:"))
        self.chat_backend_combo = QComboBox()
        self.chat_backend_combo.addItem("Built-in AI Assistant (Recommended)")
        if HAS_LLAMA:
            self.chat_backend_combo.addItem("Local TinyLLaMA")
        backend_row.addWidget(self.chat_backend_combo)

        self.context_status_label = QLabel("Ready")
        self.context_status_label.setStyleSheet("color: #a0aec0; font-style: italic;")
        backend_row.addStretch()
        backend_row.addWidget(self.context_status_label)

        layout.addLayout(backend_row)
        return tab

    def sendChatQuickQuery(self, query):
        if not self.is_activated:
            QMessageBox.warning(self, "Activation Required", "AI Chat Assistant is locked in the free edition.\nYouTube transcription is completely free. Please activate TinyLytic Pro.")
            self.showActivationDialog()
            return
        self.chat_input.setText(query)
        self.handleSendChat()

    def handleSendChat(self):
        if not self.is_activated:
            QMessageBox.warning(self, "Activation Required", "AI Chat Assistant is locked in the free edition.\nYouTube transcription is completely free. Please activate TinyLytic Pro.")
            self.showActivationDialog()
            return
        query = self.chat_input.text().strip()
        if not query:
            return

        timestamp = time.strftime("%H:%M:%S")
        user_html = (
            f"<div style='margin: 8px 0; text-align: right;'>"
            f"<span style='background-color: #2b6cb0; color: #ffffff; padding: 6px 12px; border-radius: 8px;'>"
            f"<b>You ({timestamp}):</b> {query}</span></div>"
        )
        self.chat_display.append(user_html)
        self.chat_input.clear()
        self.chat_send_btn.setEnabled(False)

        model_choice = self.chat_backend_combo.currentText()
        self.chat_worker = ChatWorker(self.chat_manager, query, model_choice)

        def on_reply(reply):
            self.chat_send_btn.setEnabled(True)
            bot_html = (
                f"<div style='margin: 8px 0;'>"
                f"<span style='color: #63b3ed; font-weight: bold;'>TinyLytic AI:</span><br>"
                f"<div style='background-color: #1a202c; color: #e2e8f0; padding: 10px; border-radius: 8px; border-left: 3px solid #63b3ed; margin-top: 4px;'>"
                f"{reply.replace(chr(10), '<br>')}</div></div>"
            )
            self.chat_display.append(bot_html)

        def on_err(err):
            self.chat_send_btn.setEnabled(True)
            self.chat_display.append(f"<div style='color: #e53e3e;'><b>Error:</b> {err}</div>")

        self.chat_worker.response_ready.connect(on_reply)
        self.chat_worker.error.connect(on_err)
        self.chat_worker.start()

    def clearChat(self):
        self.chat_display.clear()

    def sendToChat(self, text):
        """Pass any transcription into AI Chat context and switch to Chat Tab."""
        self.current_transcript_text = text
        self.chat_manager.set_context_transcript(text)
        word_count = len(text.split())
        self.context_status_label.setText(f"Context Loaded ({word_count} words)")
        self.chat_display.append(
            f"<div style='color: #38b2ac; font-weight: bold; margin: 10px 0;'>"
            f"[Loaded new transcript ({word_count} words) into Chat context]</div>"
        )
        self.tabs.setCurrentWidget(self.tab_chat)

    # =========================================================================
    # TAB 2: YOUTUBE TRANSCRIBER
    # =========================================================================
    def createYouTubeTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        url_layout = QHBoxLayout()
        self.yt_url_input = QLineEdit()
        self.yt_url_input.setPlaceholderText("Paste YouTube video link here")
        url_layout.addWidget(self.yt_url_input, 1)

        btn_paste = QPushButton("Paste")
        btn_paste.clicked.connect(lambda: self.yt_url_input.setText(pyperclip.paste()))
        url_layout.addWidget(btn_paste)

        layout.addLayout(url_layout)

        btn_row = QHBoxLayout()
        self.yt_generate_btn = QPushButton("Transcribe")
        self.yt_generate_btn.setObjectName("actionBtn")
        self.yt_generate_btn.clicked.connect(self.processYouTube)
        btn_row.addWidget(self.yt_generate_btn)

        self.yt_copy_btn = QPushButton("Copy")
        self.yt_copy_btn.clicked.connect(lambda: self.copyText(self.yt_result_box.toPlainText()))
        btn_row.addWidget(self.yt_copy_btn)

        self.yt_to_chat_btn = QPushButton("Send to Chat")
        self.yt_to_chat_btn.clicked.connect(lambda: self.sendToChat(self.yt_result_box.toPlainText()))
        btn_row.addWidget(self.yt_to_chat_btn)

        btn_row.addStretch()

        self.yt_reset_btn = QPushButton("Reset")
        self.yt_reset_btn.clicked.connect(self.resetYouTubeTab)
        btn_row.addWidget(self.yt_reset_btn)

        layout.addLayout(btn_row)

        self.yt_progress = QProgressBar()
        layout.addWidget(self.yt_progress)

        self.yt_status = QLabel("Status: Ready to transcribe")
        self.yt_status.setStyleSheet("color: #a0aec0;")
        layout.addWidget(self.yt_status)

        self.yt_result_box = QTextEdit()
        self.yt_result_box.setReadOnly(True)
        layout.addLayout(self.createResultHeaderBar(self.yt_result_box))
        layout.addWidget(self.yt_result_box, 1)

        return tab

    def setProcessingState(self, is_busy: bool, message: str = ""):
        """Globally lock or unlock header toolbar controls, tabs, and action buttons during processing."""
        # Header controls
        if hasattr(self, 'model_combo'):
            self.model_combo.setEnabled(not is_busy)
        if hasattr(self, 'lang_combo'):
            self.lang_combo.setEnabled(not is_busy)
        if hasattr(self, 'task_combo'):
            self.task_combo.setEnabled(not is_busy)
        if hasattr(self, 'chunk_spin'):
            self.chunk_spin.setEnabled(not is_busy)
        if hasattr(self, 'multi_speaker_check'):
            self.multi_speaker_check.setEnabled(not is_busy)
        if hasattr(self, 'speaker_count_spin'):
            self.speaker_count_spin.setEnabled(not is_busy)
        if hasattr(self, 'compute_combo'):
            self.compute_combo.setEnabled(not is_busy)
        if hasattr(self, 'device_combo'):
            self.device_combo.setEnabled(not is_busy)

        # Tab navigation lock
        if hasattr(self, 'tabs'):
            self.tabs.tabBar().setEnabled(not is_busy)

        # Action buttons across all tabs
        is_act = getattr(self, 'is_activated', False)
        if hasattr(self, 'yt_generate_btn'):
            self.yt_generate_btn.setEnabled(not is_busy)
        if hasattr(self, 'live_record_btn'):
            self.live_record_btn.setEnabled(not is_busy and is_act)
        if hasattr(self, 'live_process_btn'):
            self.live_process_btn.setEnabled(not is_busy and is_act and bool(getattr(self, 'recorded_wav_path', None)))
        if hasattr(self, 'audio_transcribe_btn'):
            self.audio_transcribe_btn.setEnabled(not is_busy and is_act)
        if hasattr(self, 'video_transcribe_btn'):
            self.video_transcribe_btn.setEnabled(not is_busy and is_act)
        if hasattr(self, 'btn_caption_studio'):
            self.btn_caption_studio.setEnabled(not is_busy and is_act)
        if hasattr(self, 'btn_run_slides'):
            self.btn_run_slides.setEnabled(not is_busy and is_act)
        if hasattr(self, 'btn_ocr'):
            self.btn_ocr.setEnabled(not is_busy and is_act)

        if message and hasattr(self, 'status_label'):
            self.status_label.setText(message)

        try:
            if is_busy:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            else:
                QApplication.restoreOverrideCursor()
        except Exception:
            pass

    def processYouTube(self):
        url = self.yt_url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid YouTube video link.")
            return

        self.setProcessingState(True, "Downloading audio stream from YouTube...")
        self.yt_progress.setValue(10)
        self.yt_status.setText("Status: Downloading audio stream from YouTube...")
        self.yt_result_box.clear()

        self.yt_worker = YouTubeDownloadWorker(url)

        def on_download_done(audio_path):
            self.yt_status.setText("Status: Audio downloaded. Starting AI transcription...")
            self.yt_progress.setValue(40)

            model_id = self.model_combo.currentData()
            lang = self.lang_combo.currentData()
            task = self.task_combo.currentData()
            chunk_len = self.chunk_spin.value()
            num_spk = ("auto" if self.speaker_count_spin.value() == 0 else self.speaker_count_spin.value()) if self.multi_speaker_check.isChecked() else 1

            self.active_transcription = UnifiedTranscriptionWorker(audio_path, model_id, lang, task, chunk_len, num_speakers=num_spk, device=self.get_selected_compute_device())
            self.active_transcription.progress.connect(self.yt_progress.setValue)
            self.active_transcription.status.connect(self.yt_status.setText)

            def on_transcribe_done(formatted, segments):
                self.setProcessingState(False, "YouTube transcription finished.")
                self.yt_result_box.setText(formatted)
                self.current_transcript_segments = segments
                self.current_transcript_text = formatted
                self.yt_status.setText("Status: Transcription completed successfully.")

            def on_transcribe_err(err):
                self.setProcessingState(False, "Transcription error.")
                self.yt_status.setText(f"Error: {err}")
                QMessageBox.critical(self, "Transcription Error", err)

            self.active_transcription.result.connect(on_transcribe_done)
            self.active_transcription.error.connect(on_transcribe_err)
            self.active_transcription.start()

        def on_download_err(err):
            self.setProcessingState(False, "Download error.")
            self.yt_status.setText(f"Download Error: {err}")
            QMessageBox.critical(self, "Download Error", err)

        self.yt_worker.completed.connect(on_download_done)
        self.yt_worker.error.connect(on_download_err)
        self.yt_worker.start()

    def resetYouTubeTab(self):
        self.yt_url_input.clear()
        self.yt_result_box.clear()
        self.yt_progress.setValue(0)
        self.yt_status.setText("Status: Ready")
        self.yt_generate_btn.setEnabled(True)

    # =========================================================================
    # TAB 3: REALTIME STUDIO
    # =========================================================================
    def createRealtimeTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.lock_banner_realtime = self.createLockBanner("Live Realtime Studio")
        layout.addWidget(self.lock_banner_realtime)

        dev_row = QHBoxLayout()
        dev_row.addWidget(QLabel("Microphone:"))
        self.mic_combo = QComboBox()
        if HAS_SD:
            try:
                devices = sd.query_devices()
                for idx, dev in enumerate(devices):
                    if dev.get('max_input_channels', 0) > 0:
                        self.mic_combo.addItem(f"{dev['name']}", idx)
            except Exception:
                self.mic_combo.addItem("Default Microphone", None)
        else:
            self.mic_combo.addItem("Default Microphone", None)
        dev_row.addWidget(self.mic_combo, 1)

        self.timer_label = QLabel("00:00:00")
        self.timer_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #63b3ed; padding: 0 10px;")
        dev_row.addWidget(self.timer_label)

        layout.addLayout(dev_row)

        btn_row = QHBoxLayout()
        self.live_record_btn = QPushButton("Record")
        self.live_record_btn.setObjectName("recordBtn")
        self.live_record_btn.clicked.connect(self.toggleRealtimeRecording)
        btn_row.addWidget(self.live_record_btn)

        self.live_process_btn = QPushButton("Transcribe")
        self.live_process_btn.setObjectName("transcribeBtn")
        self.live_process_btn.clicked.connect(self.processRecordedAudio)
        self.live_process_btn.setEnabled(False)
        btn_row.addWidget(self.live_process_btn)

        self.live_to_chat_btn = QPushButton("Send to Chat")
        self.live_to_chat_btn.clicked.connect(lambda: self.sendToChat(self.live_result_box.toPlainText()))
        btn_row.addWidget(self.live_to_chat_btn)

        btn_row.addStretch()

        self.live_copy_btn = QPushButton("Copy")
        self.live_copy_btn.clicked.connect(lambda: self.copyText(self.live_result_box.toPlainText()))
        btn_row.addWidget(self.live_copy_btn)

        layout.addLayout(btn_row)

        vol_layout = QHBoxLayout()
        vol_layout.addWidget(QLabel("Audio Level:"))
        self.live_vol_bar = QProgressBar()
        self.live_vol_bar.setRange(0, 100)
        self.live_vol_bar.setValue(0)
        vol_layout.addWidget(self.live_vol_bar, 1)
        layout.addLayout(vol_layout)

        self.live_status = QLabel("Status: Idle. Click 'Record' to start.")
        self.live_status.setStyleSheet("color: #a0aec0;")
        layout.addWidget(self.live_status)

        self.live_transcribe_progress = QProgressBar()
        layout.addWidget(self.live_transcribe_progress)

        self.live_result_box = QTextEdit()
        self.live_result_box.setReadOnly(True)
        layout.addLayout(self.createResultHeaderBar(self.live_result_box))
        layout.addWidget(self.live_result_box, 1)

        self.recorded_wav_path = None
        return tab

    def toggleRealtimeRecording(self):
        if not self.is_recording:
            if not self.is_activated:
                QMessageBox.warning(self, "Activation Required", "Live Realtime Recording is locked.\nPlease activate TinyLytic with a valid license key.")
                self.showActivationDialog()
                return

            self.is_recording = True
            self.live_record_btn.setText("Stop")
            self.live_record_btn.setStyleSheet("background-color: #8b0000; color: #ffffff; font-weight: bold;")
            self.live_status.setText("Status: Recording audio from microphone...")
            self.live_process_btn.setEnabled(False)

            dev_idx = self.mic_combo.currentData()
            self.recorder_worker = RealtimeRecorderWorker(device_index=dev_idx)

            self.recorder_worker.volume_level.connect(lambda vol: self.live_vol_bar.setValue(int(vol * 100)))
            self.recorder_worker.recording_time.connect(self.timer_label.setText)

            def on_recording_done(wav_path):
                self.recorded_wav_path = wav_path
                self.live_status.setText(f"Status: Recording finished and saved: {os.path.basename(wav_path)}")
                self.live_process_btn.setEnabled(True)
                self.live_vol_bar.setValue(0)

            def on_recording_err(err):
                self.live_status.setText(f"Recording Error: {err}")
                QMessageBox.critical(self, "Recording Error", err)

            self.recorder_worker.finished_recording.connect(on_recording_done)
            self.recorder_worker.error.connect(on_recording_err)
            self.recorder_worker.start()
        else:
            self.is_recording = False
            self.live_record_btn.setText("Record")
            self.live_record_btn.setStyleSheet("background-color: #d9383a; color: #ffffff; font-weight: bold;")
            if self.recorder_worker:
                self.recorder_worker.stop()

    def processRecordedAudio(self):
        if not self.is_activated:
            QMessageBox.warning(self, "Activation Required", "Live Recording transcription is locked in the free edition.\nYouTube transcription is completely free. Please activate TinyLytic with a valid license key.")
            self.showActivationDialog()
            return

        if not self.recorded_wav_path or not os.path.exists(self.recorded_wav_path):
            QMessageBox.warning(self, "No Audio", "Please record audio before transcribing.")
            return

        self.setProcessingState(True, "Transcribing live recording...")
        self.live_status.setText("Status: Transcribing live recording...")
        self.live_transcribe_progress.setValue(10)

        model_id = self.model_combo.currentData()
        lang = self.lang_combo.currentData()
        task = self.task_combo.currentData()
        chunk_len = self.chunk_spin.value()
        num_spk = ("auto" if self.speaker_count_spin.value() == 0 else self.speaker_count_spin.value()) if self.multi_speaker_check.isChecked() else 1

        self.live_transcribe_worker = UnifiedTranscriptionWorker(self.recorded_wav_path, model_id, lang, task, chunk_len, num_speakers=num_spk, device=self.get_selected_compute_device())
        self.live_transcribe_worker.progress.connect(self.live_transcribe_progress.setValue)
        self.live_transcribe_worker.status.connect(self.live_status.setText)

        def on_done(formatted, segments):
            self.setProcessingState(False, "Recording transcription complete.")
            self.live_result_box.setText(formatted)
            self.current_transcript_segments = segments
            self.current_transcript_text = formatted
            self.live_status.setText("Status: Transcription completed successfully.")

        def on_err(err):
            self.setProcessingState(False, "Transcription error.")
            self.live_status.setText(f"Error: {err}")
            QMessageBox.critical(self, "Transcription Error", err)

        self.live_transcribe_worker.result.connect(on_done)
        self.live_transcribe_worker.error.connect(on_err)
        self.live_transcribe_worker.start()

    # =========================================================================
    # TAB 4: AUDIO FILE TRANSCRIBER
    # =========================================================================
    def createAudioTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.lock_banner_audio = self.createLockBanner("Audio File Transcription")
        layout.addWidget(self.lock_banner_audio)

        file_row = QHBoxLayout()
        self.audio_path_input = QLineEdit()
        self.audio_path_input.setPlaceholderText("Select an audio file (.mp3, .wav, .m4a, .flac, .ogg, .aac, .webm)...")
        file_row.addWidget(self.audio_path_input, 1)

        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browseAudioFile)
        file_row.addWidget(btn_browse)

        layout.addLayout(file_row)

        action_row = QHBoxLayout()
        self.audio_transcribe_btn = QPushButton("Transcribe")
        self.audio_transcribe_btn.setObjectName("actionBtn")
        self.audio_transcribe_btn.clicked.connect(self.processAudioFile)
        action_row.addWidget(self.audio_transcribe_btn)

        btn_copy = QPushButton("Copy")
        btn_copy.clicked.connect(lambda: self.copyText(self.audio_result_box.toPlainText()))
        action_row.addWidget(btn_copy)

        btn_chat = QPushButton("Send to Chat")
        btn_chat.clicked.connect(lambda: self.sendToChat(self.audio_result_box.toPlainText()))
        action_row.addWidget(btn_chat)

        action_row.addStretch()
        layout.addLayout(action_row)

        self.audio_progress = QProgressBar()
        layout.addWidget(self.audio_progress)

        self.audio_status = QLabel("Status: Select an audio file to transcribe.")
        self.audio_status.setStyleSheet("color: #a0aec0;")
        layout.addWidget(self.audio_status)

        self.audio_result_box = QTextEdit()
        self.audio_result_box.setReadOnly(True)
        layout.addLayout(self.createResultHeaderBar(self.audio_result_box))
        layout.addWidget(self.audio_result_box, 1)

        return tab

    def browseAudioFile(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Audio File", "", "Audio Files (*.mp3 *.wav *.m4a *.flac *.ogg *.aac *.webm);;All Files (*.*)"
        )
        if path:
            self.audio_path_input.setText(path)

    def processAudioFile(self):
        if not self.is_activated:
            QMessageBox.warning(self, "Activation Required", "Audio file transcription is locked in the free edition.\nYouTube transcription is completely free. Please activate TinyLytic with a valid license key.")
            self.showActivationDialog()
            return

        path = self.audio_path_input.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Invalid File", "Please select a valid audio file.")
            return

        self.setProcessingState(True, "Transcribing audio file...")
        self.audio_progress.setValue(10)
        self.audio_status.setText("Status: Transcribing audio file...")

        model_id = self.model_combo.currentData()
        lang = self.lang_combo.currentData()
        task = self.task_combo.currentData()
        chunk_len = self.chunk_spin.value()
        num_spk = ("auto" if self.speaker_count_spin.value() == 0 else self.speaker_count_spin.value()) if self.multi_speaker_check.isChecked() else 1

        self.audio_worker = UnifiedTranscriptionWorker(path, model_id, lang, task, chunk_len, num_speakers=num_spk, device=self.get_selected_compute_device())
        self.audio_worker.progress.connect(self.audio_progress.setValue)
        self.audio_worker.status.connect(self.audio_status.setText)

        def on_done(formatted, segments):
            self.setProcessingState(False, "Audio transcription finished.")
            self.audio_result_box.setText(formatted)
            self.current_transcript_segments = segments
            self.current_transcript_text = formatted
            self.audio_status.setText("Status: Transcription completed successfully.")

        def on_err(err):
            self.setProcessingState(False, "Transcription error.")
            self.audio_status.setText(f"Error: {err}")
            QMessageBox.critical(self, "Transcription Error", err)

        self.audio_worker.result.connect(on_done)
        self.audio_worker.error.connect(on_err)
        self.audio_worker.start()

    # =========================================================================
    # TAB 5: VIDEO FILE TRANSCRIBER
    # =========================================================================
    def createVideoTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.lock_banner_video = self.createLockBanner("Video Transcription & Caption Studio")
        layout.addWidget(self.lock_banner_video)

        file_row = QHBoxLayout()
        self.video_path_input = QLineEdit()
        self.video_path_input.setPlaceholderText("Select a video file (.mp4, .mkv, .mov, .avi, .webm, .flv)...")
        file_row.addWidget(self.video_path_input, 1)

        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browseVideoFile)
        file_row.addWidget(btn_browse)

        layout.addLayout(file_row)

        action_row = QHBoxLayout()
        self.video_transcribe_btn = QPushButton("Transcribe")
        self.video_transcribe_btn.setObjectName("actionBtn")
        self.video_transcribe_btn.clicked.connect(self.processVideoFile)
        action_row.addWidget(self.video_transcribe_btn)

        self.btn_caption_studio = QPushButton("Insert / Caption Studio")
        self.btn_caption_studio.setStyleSheet("background-color: #805ad5; color: #ffffff; font-weight: bold;")
        self.btn_caption_studio.clicked.connect(self.openVideoCaptionStudio)
        action_row.addWidget(self.btn_caption_studio)

        btn_copy = QPushButton("Copy")
        btn_copy.clicked.connect(lambda: self.copyText(self.video_result_box.toPlainText()))
        action_row.addWidget(btn_copy)

        btn_chat = QPushButton("Send to Chat")
        btn_chat.clicked.connect(lambda: self.sendToChat(self.video_result_box.toPlainText()))
        action_row.addWidget(btn_chat)

        action_row.addStretch()
        layout.addLayout(action_row)

        self.video_progress = QProgressBar()
        layout.addWidget(self.video_progress)

        self.video_status = QLabel("Status: Select a video file to transcribe.")
        self.video_status.setStyleSheet("color: #a0aec0;")
        layout.addWidget(self.video_status)

        self.video_result_box = QTextEdit()
        self.video_result_box.setReadOnly(True)
        layout.addLayout(self.createResultHeaderBar(self.video_result_box))
        layout.addWidget(self.video_result_box, 1)

        return tab

    def browseVideoFile(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Video File", "", "Video Files (*.mp4 *.mkv *.mov *.avi *.webm *.flv);;All Files (*.*)"
        )
        if path:
            self.video_path_input.setText(path)

    def openVideoCaptionStudio(self):
        if not self.is_activated:
            QMessageBox.warning(self, "Activation Required", "Video Caption Studio is locked.\nPlease activate TinyLytic with a valid license key.")
            self.showActivationDialog()
            return

        path = self.video_path_input.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "No Video Selected", "Please select a valid video file first using Browse.")
            return

        from video_caption_studio import VideoCaptionStudioDialog
        dlg = VideoCaptionStudioDialog(self, path, self.current_transcript_segments)
        dlg.exec()

    def processVideoFile(self):
        if not self.is_activated:
            QMessageBox.warning(self, "Activation Required", "Video transcription is locked in the free edition.\nYouTube transcription is completely free. Please activate TinyLytic with a valid license key.")
            self.showActivationDialog()
            return

        path = self.video_path_input.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Invalid File", "Please select a valid video file.")
            return

        self.setProcessingState(True, "Extracting audio stream via FFmpeg...")
        self.video_progress.setValue(10)
        self.video_status.setText("Status: Extracting audio stream via FFmpeg...")

        out_wav = os.path.join(TEMP_DIR, f"extracted_{int(time.time())}.wav")
        ffmpeg_bin = setup_ffmpeg() or "ffmpeg"
        cmd = [ffmpeg_bin, "-y", "-i", path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", out_wav]

        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            self.video_status.setText("Status: Audio extracted successfully. Transcribing...")
            self.video_progress.setValue(35)

            model_id = self.model_combo.currentData()
            lang = self.lang_combo.currentData()
            task = self.task_combo.currentData()
            chunk_len = self.chunk_spin.value()
            num_spk = ("auto" if self.speaker_count_spin.value() == 0 else self.speaker_count_spin.value()) if self.multi_speaker_check.isChecked() else 1

            self.video_worker = UnifiedTranscriptionWorker(out_wav, model_id, lang, task, chunk_len, num_speakers=num_spk, device=self.get_selected_compute_device())
            self.video_worker.progress.connect(self.video_progress.setValue)
            self.video_worker.status.connect(self.video_status.setText)

            def on_done(formatted, segments):
                self.setProcessingState(False, "Video transcription finished.")
                self.video_result_box.setText(formatted)
                self.current_transcript_segments = segments
                self.current_transcript_text = formatted
                self.video_status.setText("Status: Transcription completed successfully.")

            def on_err(err):
                self.setProcessingState(False, "Transcription error.")
                self.video_status.setText(f"Error: {err}")
                QMessageBox.critical(self, "Transcription Error", err)

            self.video_worker.result.connect(on_done)
            self.video_worker.error.connect(on_err)
            self.video_worker.start()

        except Exception as e:
            self.setProcessingState(False, "Extraction error.")
            self.video_status.setText(f"Extraction Error: {str(e)}")
            QMessageBox.critical(self, "Extraction Error", f"Failed to extract audio from video: {str(e)}")

    # =========================================================================
    # TAB 6: OCR AND VISION
    # =========================================================================
    def createVisionTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.lock_banner_vision = self.createLockBanner("Video Slide Detection & OCR")
        layout.addWidget(self.lock_banner_vision)

        vision_tabs = QTabWidget()

        # Video Slide Detector
        slide_tab = QWidget()
        slide_layout = QVBoxLayout(slide_tab)

        v_row = QHBoxLayout()
        self.vision_video_input = QLineEdit()
        self.vision_video_input.setPlaceholderText("Select video to extract slide transition timestamps and headers...")
        v_row.addWidget(self.vision_video_input, 1)

        btn_browse_v = QPushButton("Browse")
        btn_browse_v.clicked.connect(self.browseVisionVideo)
        v_row.addWidget(btn_browse_v)
        slide_layout.addLayout(v_row)

        action_row = QHBoxLayout()
        self.btn_run_slides = QPushButton("Detect Slides")
        self.btn_run_slides.setObjectName("actionBtn")
        self.btn_run_slides.clicked.connect(self.processVideoSlides)
        action_row.addWidget(self.btn_run_slides)

        btn_copy_v = QPushButton("Copy")
        btn_copy_v.clicked.connect(lambda: self.copyText(self.vision_result_box.toPlainText()))
        action_row.addWidget(btn_copy_v)

        btn_chat_v = QPushButton("Send to Chat")
        btn_chat_v.clicked.connect(lambda: self.sendToChat(self.vision_result_box.toPlainText()))
        action_row.addWidget(btn_chat_v)

        action_row.addStretch()
        slide_layout.addLayout(action_row)

        self.vision_progress = QProgressBar()
        slide_layout.addWidget(self.vision_progress)

        self.vision_status = QLabel("Status: Select a video to detect slide transitions.")
        self.vision_status.setStyleSheet("color: #a0aec0;")
        slide_layout.addWidget(self.vision_status)

        self.vision_result_box = QTextEdit()
        self.vision_result_box.setReadOnly(True)
        slide_layout.addWidget(self.vision_result_box, 1)

        vision_tabs.addTab(slide_tab, "Video Slide Detector")

        # Image OCR
        img_tab = QWidget()
        img_layout = QVBoxLayout(img_tab)

        i_row = QHBoxLayout()
        self.vision_img_input = QLineEdit()
        self.vision_img_input.setPlaceholderText("Select an image file (.png, .jpg, .bmp, .webp, screenshot)...")
        i_row.addWidget(self.vision_img_input, 1)

        btn_browse_img = QPushButton("Browse")
        btn_browse_img.clicked.connect(self.browseVisionImage)
        i_row.addWidget(btn_browse_img)
        img_layout.addLayout(i_row)

        self.btn_ocr = QPushButton("Extract Text")
        self.btn_ocr.setObjectName("actionBtn")
        self.btn_ocr.clicked.connect(self.processImageOCR)
        img_layout.addWidget(self.btn_ocr)

        self.ocr_status = QLabel("Status: Ready to extract text.")
        self.ocr_status.setStyleSheet("color: #a0aec0;")
        img_layout.addWidget(self.ocr_status)

        self.ocr_result_box = QTextEdit()
        self.ocr_result_box.setReadOnly(True)
        img_layout.addWidget(self.ocr_result_box, 1)

        vision_tabs.addTab(img_tab, "Image OCR")

        layout.addWidget(vision_tabs)
        return tab

    def browseVisionVideo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Video for Slide Detection", "", "Video Files (*.mp4 *.mkv *.mov *.avi *.webm)"
        )
        if path:
            self.vision_video_input.setText(path)

    def processVideoSlides(self):
        if not self.is_activated:
            QMessageBox.warning(self, "Activation Required", "Video slide detection is locked in the free edition.\nYouTube transcription is completely free. Please activate TinyLytic with a valid license key.")
            self.showActivationDialog()
            return

        path = self.vision_video_input.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Invalid Video", "Please select a valid video file.")
            return

        self.setProcessingState(True, "Analyzing video slide transitions...")
        self.vision_status.setText("Status: Analyzing video frames with OpenCV...")
        self.vision_progress.setValue(10)

        self.slide_worker = VisionAnalysisWorker(mode="video_slides", file_path=path, interval_sec=4)
        self.slide_worker.progress.connect(self.vision_progress.setValue)
        self.slide_worker.status.connect(self.vision_status.setText)

        def on_done(res):
            self.setProcessingState(False, "Slide detection complete.")
            self.vision_result_box.setText(res.get("formatted_text", ""))
            self.vision_status.setText("Status: Slide detection complete.")

        def on_err(err):
            self.setProcessingState(False, "Slide detection error.")
            self.vision_status.setText(f"Error: {err}")
            QMessageBox.critical(self, "Vision Error", err)

        self.slide_worker.result.connect(on_done)
        self.slide_worker.error.connect(on_err)
        self.slide_worker.start()

    def browseVisionImage(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image for OCR", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)"
        )
        if path:
            self.vision_img_input.setText(path)

    def processImageOCR(self):
        if not self.is_activated:
            QMessageBox.warning(self, "Activation Required", "Image OCR is locked in the free edition.\nYouTube transcription is completely free. Please activate TinyLytic with a valid license key.")
            self.showActivationDialog()
            return

        path = self.vision_img_input.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Invalid Image", "Please select a valid image file.")
            return

        self.setProcessingState(True, "Extracting text from image via OCR...")
        self.ocr_status.setText("Status: Processing image with OpenCV...")
        self.img_worker = VisionAnalysisWorker(mode="image_ocr", file_path=path)

        def on_done(res):
            self.setProcessingState(False, "OCR text extraction finished.")
            self.ocr_status.setText(res.get("message", "Done."))
            self.ocr_result_box.setText(res.get("text", ""))

        def on_err(err):
            self.setProcessingState(False, "OCR error.")
            self.ocr_status.setText(f"Error: {err}")
            QMessageBox.critical(self, "OCR Error", err)

        self.img_worker.result.connect(on_done)
        self.img_worker.error.connect(on_err)
        self.img_worker.start()

    def get_selected_compute_device(self):
        """Retrieve user-selected compute hardware device."""
        if hasattr(self, 'device_combo') and self.device_combo is not None:
            return self.device_combo.currentData() or "auto"
        return "auto"

    def refresh_model_dropdown(self):
        """Refresh the Model dropdown across the application."""
        curr_id = self.model_combo.currentData()
        self.model_combo.clear()
        models = get_available_whisper_models()
        for m in models:
            self.model_combo.addItem(m["name"], m["id"])
        idx = self.model_combo.findData(curr_id)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        else:
            self.model_combo.setCurrentIndex(0)

    # =========================================================================
    # TAB 7: SETTINGS
    # =========================================================================
    def createSettingsTab(self):
        tab = QWidget()
        scroll = QScrollArea(tab)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(14)
        layout.setContentsMargins(12, 12, 12, 12)

        specs = get_system_specs()

        # 1. Hardware Specs & Acceleration Group
        hw_group = QGroupBox("System Hardware and Acceleration")
        hw_layout = QFormLayout(hw_group)
        hw_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        hw_layout.addRow("Processor:", QLabel(f"<b>{specs['cpu']}</b>"))
        hw_layout.addRow("System RAM:", QLabel(f"{specs['ram_str']}"))

        # Detected GPU & VRAM
        gpu_display = f"<b>{specs['gpu_name']}</b> ({specs['gpu_vram_gb']} GB VRAM)"
        if specs.get("driver_version"):
            gpu_display += f" | Driver: {specs['driver_version']}"
        hw_layout.addRow("Detected GPU:", QLabel(gpu_display))

        # CUDA Acceleration Status
        if specs["has_cuda"]:
            cuda_status_txt = f"<span style='color: #48bb78; font-weight: bold;'>Active (CUDA {specs.get('cuda_version', '')} Hardware Acceleration Enabled)</span>"
            hw_layout.addRow("CUDA Status:", QLabel(cuda_status_txt))
        elif specs["cuda_capable"]:
            cuda_box = QHBoxLayout()
            cuda_lbl = QLabel(f"<span style='color: #ecc94b; font-weight: bold;'>NVIDIA {specs['gpu_name']} Detected (12 GB VRAM). PyTorch CUDA package needed to activate GPU.</span>")
            cuda_box.addWidget(cuda_lbl)

            self.btn_install_cuda = QPushButton("Enable CUDA GPU Acceleration")
            self.btn_install_cuda.setStyleSheet("background-color: #276749; color: #ffffff; font-weight: bold; padding: 6px 14px;")
            self.btn_install_cuda.clicked.connect(self.installCudaSupport)
            cuda_box.addWidget(self.btn_install_cuda)
            hw_layout.addRow("CUDA Status:", cuda_box)
        else:
            hw_layout.addRow("CUDA Status:", QLabel("<span style='color: #a0aec0;'>CPU Execution Mode (No CUDA GPU detected)</span>"))

        # Compute Device Selector
        self.device_combo = QComboBox()
        for dev in specs["available_devices"]:
            self.device_combo.addItem(dev["name"], dev["id"])
        self.device_combo.setCurrentIndex(0)
        self.device_combo.setStyleSheet("padding: 6px; font-weight: bold;")
        hw_layout.addRow("Compute Device:", self.device_combo)

        # CUDA Installation Progress Bar & Status
        self.cuda_install_status = QLabel("")
        self.cuda_install_status.setVisible(False)
        self.cuda_install_progress = QProgressBar()
        self.cuda_install_progress.setVisible(False)
        hw_layout.addRow(self.cuda_install_status, self.cuda_install_progress)

        layout.addWidget(hw_group)

        # 2. AI Model Manager & Recommendations Group
        model_group = QGroupBox("Model Manager and Hardware Recommendations")
        model_layout = QVBoxLayout(model_group)

        rec_banner = QLabel(f"<b>Hardware Recommendation:</b> {specs['recommended_model_tier']}")
        rec_banner.setStyleSheet("background-color: #1e2638; border: 1px solid #3182ce; padding: 10px; border-radius: 6px; color: #63b3ed;")
        model_layout.addWidget(rec_banner)

        models_dir = resource_path("models")
        self.model_status_labels = {}
        self.model_action_buttons = {}

        for key, info in WHISPER_DOWNLOAD_CATALOG.items():
            row_box = QHBoxLayout()
            target_file = os.path.join(models_dir, info["filename"])
            is_installed = os.path.exists(target_file)

            name_lbl = QLabel(f"<b>{info['name']}</b> ({info['size_str']})")
            name_lbl.setFixedWidth(190)
            desc_lbl = QLabel(f"{info['desc']} [{info['vram_req']}]")

            status_lbl = QLabel("<span style='color: #48bb78; font-weight: bold;'>Installed</span>" if is_installed else "<span style='color: #a0aec0;'>Not Downloaded</span>")
            status_lbl.setFixedWidth(120)
            self.model_status_labels[key] = status_lbl

            btn_dl = QPushButton("Installed" if is_installed else "Download")
            btn_dl.setEnabled(not is_installed)
            btn_dl.setFixedWidth(110)
            if is_installed:
                btn_dl.setStyleSheet("background-color: #2d3748; color: #a0aec0;")
            else:
                btn_dl.setStyleSheet("background-color: #3182ce; color: #ffffff; font-weight: bold;")
            btn_dl.clicked.connect(lambda checked, k=key: self.startModelDownload(k))
            self.model_action_buttons[key] = btn_dl

            row_box.addWidget(name_lbl)
            row_box.addWidget(desc_lbl, 1)
            row_box.addWidget(status_lbl)
            row_box.addWidget(btn_dl)
            model_layout.addLayout(row_box)

        # Model Download Progress Bar & Status
        self.model_dl_status = QLabel("")
        self.model_dl_status.setVisible(False)
        self.model_dl_progress = QProgressBar()
        self.model_dl_progress.setVisible(False)
        model_layout.addWidget(self.model_dl_status)
        model_layout.addWidget(self.model_dl_progress)

        layout.addWidget(model_group)

        # 3. Software Libraries Group
        sw_group = QGroupBox("Runtime Module Status")
        sw_layout = QFormLayout(sw_group)

        ffmpeg_status = "Available" if setup_ffmpeg() else "Missing"
        cv2_status = "Enabled" if HAS_CV2 else "Missing"
        tess_status = "Enabled" if HAS_PYTESSERACT else "Optional"
        llama_status = "Enabled" if HAS_LLAMA else "Optional"

        sw_layout.addRow("FFmpeg Engine:", QLabel(ffmpeg_status))
        sw_layout.addRow("OpenCV (cv2):", QLabel(cv2_status))
        sw_layout.addRow("OCR Module:", QLabel(tess_status))
        sw_layout.addRow("LLaMA Backend:", QLabel(llama_status))

        layout.addWidget(sw_group)

        # 4. Package Updates and Maintenance Group
        pkg_group = QGroupBox("Package Updates and Maintenance")
        pkg_layout = QVBoxLayout(pkg_group)

        pkg_info_row = QHBoxLayout()
        try:
            import yt_dlp
            ytdlp_ver = getattr(yt_dlp.version, '__version__', 'Installed')
        except Exception:
            ytdlp_ver = "Not installed"
        self.lbl_ytdlp_ver = QLabel(f"<b>yt-dlp Engine Version:</b> {ytdlp_ver}")
        self.lbl_ytdlp_ver.setStyleSheet("color: #e2e8f0;")
        pkg_info_row.addWidget(self.lbl_ytdlp_ver, 1)

        btn_update_ytdlp = QPushButton("Update yt-dlp")
        btn_update_ytdlp.setStyleSheet("background-color: #2b6cb0; color: #ffffff; font-weight: bold; padding: 6px 14px;")
        btn_update_ytdlp.clicked.connect(self.updateYtDlp)
        pkg_info_row.addWidget(btn_update_ytdlp)

        btn_update_all = QPushButton("Update Core Packages (yt-dlp, whisper)")
        btn_update_all.setStyleSheet("background-color: #2b354f; color: #63b3ed; font-weight: bold; padding: 6px 14px;")
        btn_update_all.clicked.connect(self.updateCorePackages)
        pkg_info_row.addWidget(btn_update_all)

        pkg_layout.addLayout(pkg_info_row)

        self.pkg_update_status = QLabel("")
        self.pkg_update_status.setVisible(False)
        self.pkg_update_progress = QProgressBar()
        self.pkg_update_progress.setVisible(False)
        pkg_layout.addWidget(self.pkg_update_status)
        pkg_layout.addWidget(self.pkg_update_progress)

        layout.addWidget(pkg_group)

        # 4. Background Process Terminal and Diagnostics
        term_group = QGroupBox("Background Process Terminal and Diagnostics")
        term_layout = QVBoxLayout(term_group)

        term_controls = QHBoxLayout()
        self.lbl_console_status = QLabel("Terminal Window: Hidden (Running cleanly in background)")
        self.lbl_console_status.setStyleSheet("color: #a0aec0; font-size: 9pt;")
        term_controls.addWidget(self.lbl_console_status, 1)

        self.btn_toggle_terminal = QPushButton("Show Terminal Window")
        self.btn_toggle_terminal.setStyleSheet("background-color: #2b354f; color: #63b3ed; font-weight: bold; padding: 6px 14px;")
        self.btn_toggle_terminal.clicked.connect(self.toggleConsoleWindow)
        term_controls.addWidget(self.btn_toggle_terminal)

        btn_clear_log = QPushButton("Clear Log")
        btn_clear_log.setStyleSheet("background-color: #2d3748; color: #e2e8f0; padding: 6px 12px;")
        btn_clear_log.clicked.connect(self.clearTerminalLog)
        term_controls.addWidget(btn_clear_log)

        term_layout.addLayout(term_controls)

        self.term_log_edit = QTextEdit()
        self.term_log_edit.setReadOnly(True)
        self.term_log_edit.setStyleSheet(
            "background-color: #0b0e14; color: #58a6ff; font-family: 'Consolas', monospace; font-size: 9pt; border: 1px solid #30363d; border-radius: 6px; padding: 6px;"
        )
        self.term_log_edit.setFixedHeight(150)
        self.term_log_edit.setPlaceholderText("Live background terminal stream and diagnostic output...")
        term_layout.addWidget(self.term_log_edit)

        layout.addWidget(term_group)

        # 5. Action Buttons (Benchmark, Activation, Clear)
        btn_box = QHBoxLayout()
        btn_bench = QPushButton("Benchmark")
        btn_bench.setObjectName("actionBtn")
        btn_bench.clicked.connect(self.runBenchmark)
        btn_box.addWidget(btn_bench)

        btn_act = QPushButton("Activation")
        btn_act.clicked.connect(self.showActivationDialog)
        btn_box.addWidget(btn_act)

        btn_clean = QPushButton("Clear")
        btn_clean.clicked.connect(self.clearTempCache)
        btn_box.addWidget(btn_clean)

        layout.addLayout(btn_box)
        layout.addStretch()

        scroll.setWidget(scroll_content)
        outer_layout = QVBoxLayout(tab)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)
        return tab

    def toggleConsoleWindow(self):
        """Toggle the visibility of the Windows command prompt terminal."""
        hwnd = get_console_hwnd()
        if not hwnd:
            QMessageBox.information(
                self, "Console Terminal",
                "No standalone console attached (running directly in windowed mode).\n"
                "You can monitor all background operations in the live terminal log above."
            )
            return

        if is_console_visible():
            hide_console()
            self.btn_toggle_terminal.setText("Show Terminal Window")
            self.lbl_console_status.setText("Terminal Window: Hidden (Running cleanly in background)")
        else:
            show_console()
            self.btn_toggle_terminal.setText("Hide Terminal Window")
            self.lbl_console_status.setText("Terminal Window: Visible (Showing command prompt)")

    def clearTerminalLog(self):
        """Clear the in-app terminal diagnostic log."""
        if hasattr(self, 'term_log_edit'):
            self.term_log_edit.clear()

    def appendTerminalLog(self, text):
        """Append real-time stdout / stderr messages to the Settings terminal viewer."""
        if hasattr(self, 'term_log_edit') and text:
            try:
                self.term_log_edit.moveCursor(QTextCursor.MoveOperation.End)
                self.term_log_edit.insertPlainText(text)
                self.term_log_edit.moveCursor(QTextCursor.MoveOperation.End)
            except Exception:
                pass

    def createResultHeaderBar(self, text_edit):
        """Create a dedicated transcript toolbar with Clean Text, Chapters, Copy, and Clear."""
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 4, 0, 4)

        lbl = QLabel("<b>Transcript Output:</b>")
        lbl.setStyleSheet("color: #63b3ed;")
        bar.addWidget(lbl)
        bar.addStretch()

        btn_clean = QPushButton("Clean Text")
        btn_clean.setStyleSheet("padding: 4px 10px; font-size: 9pt; background-color: #2b354f; color: #63b3ed; font-weight: bold;")
        btn_clean.clicked.connect(lambda: self.cleanResultBox(text_edit))
        bar.addWidget(btn_clean)

        btn_chapters = QPushButton("Chapters")
        btn_chapters.setStyleSheet("padding: 4px 10px; font-size: 9pt; background-color: #2b354f; color: #63b3ed; font-weight: bold;")
        btn_chapters.clicked.connect(lambda: self.chaptersResultBox(text_edit))
        bar.addWidget(btn_chapters)

        btn_copy = QPushButton("Copy")
        btn_copy.setStyleSheet("padding: 4px 10px; font-size: 9pt; background-color: #2d3748; color: #ffffff;")
        btn_copy.clicked.connect(lambda: self.copyText(text_edit.toPlainText()))
        bar.addWidget(btn_copy)

        btn_clear = QPushButton("Clear")
        btn_clear.setStyleSheet("padding: 4px 10px; font-size: 9pt; background-color: #2d3748; color: #ffffff;")
        btn_clear.clicked.connect(text_edit.clear)
        bar.addWidget(btn_clear)

        return bar

    def cleanResultBox(self, text_edit):
        """Switch the specified result box to pure clean reading text."""
        raw = text_edit.toPlainText().strip()
        if not raw:
            return
        cleaned = clean_transcript_text(self.current_transcript_segments or raw)
        text_edit.setPlainText(cleaned)
        self.status_label.setText("Clean transcript displayed (timestamps stripped).")

    def chaptersResultBox(self, text_edit):
        """Switch the specified result box to formatted chapter timestamps."""
        if self.current_transcript_segments:
            chapters = segments_to_chapters(
                self.current_transcript_segments,
                max_chunk_len=self.chunk_spin.value(),
                include_speaker=(self.multi_speaker_check.isChecked()),
                include_lang=True
            )
            text_edit.setPlainText(chapters)
            self.status_label.setText("Formatted chapter timestamps displayed.")
        elif self.current_transcript_text:
            text_edit.setPlainText(self.current_transcript_text)

    def cleanCurrentTranscript(self):
        """Strip timestamps and speaker headers to display clean reading paragraphs."""
        active_box = None
        curr_tab = self.tabs.currentIndex()
        if curr_tab == 1:
            active_box = self.yt_result_box
        elif curr_tab == 2:
            active_box = self.live_result_box
        elif curr_tab == 3:
            active_box = self.audio_result_box
        elif curr_tab == 4:
            active_box = self.video_result_box

        raw = active_box.toPlainText() if active_box else (self.current_transcript_text or "")
        if not raw.strip():
            QMessageBox.information(self, "Clean Transcript", "No transcript available to clean.")
            return

        cleaned = clean_transcript_text(self.current_transcript_segments or raw)
        if active_box:
            active_box.setPlainText(cleaned)
        self.status_label.setText("Clean transcript generated (timestamps stripped).")

    def startModelDownload(self, model_key):
        """Initiate background download of a Whisper model."""
        if not self.is_activated:
            QMessageBox.warning(self, "Activation Required", "Model downloading is a Pro feature.\nYouTube transcription is free. Please activate TinyLytic with a valid license key.")
            self.showActivationDialog()
            return

        info = WHISPER_DOWNLOAD_CATALOG.get(model_key)
        if not info:
            return

        target_path = os.path.join(resource_path("models"), info["filename"])
        self.model_dl_progress.setVisible(True)
        self.model_dl_status.setVisible(True)
        self.model_dl_progress.setValue(0)
        self.model_dl_status.setText(f"Connecting to download {info['name']} ({info['size_str']})...")

        if model_key in self.model_action_buttons:
            self.model_action_buttons[model_key].setEnabled(False)
            self.model_action_buttons[model_key].setText("Downloading...")

        self.dl_worker = ModelDownloadWorker(model_key, info["url"], target_path)
        self.dl_worker.progress.connect(self.model_dl_progress.setValue)
        self.dl_worker.status.connect(self.model_dl_status.setText)

        def on_download_done(key, success, msg):
            if success:
                self.model_dl_status.setText(f"Success: {msg}")
                if key in self.model_status_labels:
                    self.model_status_labels[key].setText("<span style='color: #48bb78; font-weight: bold;'>Installed</span>")
                if key in self.model_action_buttons:
                    self.model_action_buttons[key].setText("Installed")
                    self.model_action_buttons[key].setEnabled(False)
                    self.model_action_buttons[key].setStyleSheet("background-color: #2d3748; color: #a0aec0;")
                self.refresh_model_dropdown()
                QMessageBox.information(self, "Download Complete", f"Model {key} is ready to use.")
            else:
                self.model_dl_status.setText(f"Error: {msg}")
                if key in self.model_action_buttons:
                    self.model_action_buttons[key].setText("Download")
                    self.model_action_buttons[key].setEnabled(True)
                QMessageBox.warning(self, "Download Failed", msg)

        self.dl_worker.finished.connect(on_download_done)
        self.dl_worker.start()

    def updateYtDlp(self):
        self.runPackageUpdate(["yt-dlp"])

    def updateCorePackages(self):
        self.runPackageUpdate(["yt-dlp", "openai-whisper"])

    def runPackageUpdate(self, packages):
        if hasattr(self, 'pkg_worker') and self.pkg_worker.isRunning():
            QMessageBox.information(self, "Update in Progress", "Package update is already running in background.")
            return

        self.pkg_update_status.setVisible(True)
        self.pkg_update_progress.setVisible(True)
        self.pkg_update_progress.setValue(10)
        self.pkg_update_status.setText("Checking and updating packages...")

        self.pkg_worker = PackageUpdateWorker(packages)
        self.pkg_worker.progress.connect(self.pkg_update_progress.setValue)
        self.pkg_worker.status.connect(self.pkg_update_status.setText)

        def on_done(success, msg):
            self.pkg_update_progress.setValue(100 if success else 0)
            if success:
                try:
                    import yt_dlp
                    import importlib
                    importlib.reload(yt_dlp.version)
                    new_ver = getattr(yt_dlp.version, '__version__', 'Updated')
                    self.lbl_ytdlp_ver.setText(f"<b>yt-dlp Engine Version:</b> {new_ver}")
                except Exception:
                    pass
                QMessageBox.information(self, "Update Complete", f"Packages updated successfully!\n{msg}")
            else:
                QMessageBox.warning(self, "Update Warning", f"Package update completed with notices:\n{msg}")

        self.pkg_worker.finished.connect(on_done)
        self.pkg_worker.start()

    def installCudaSupport(self):
        """Install PyTorch CUDA support in background via pip."""
        if not self.is_activated:
            QMessageBox.warning(self, "Activation Required", "CUDA Hardware Acceleration installer is a Pro feature.\nPlease activate TinyLytic with a valid license key.")
            self.showActivationDialog()
            return

        reply = QMessageBox.question(
            self,
            "Install PyTorch CUDA Acceleration",
            "This will download and install PyTorch with CUDA 12.4 support for your NVIDIA GeForce RTX 3060.\n\n"
            "This provides 10x-20x faster transcription speed using your 12 GB GPU.\n\n"
            "Proceed with installation in the background?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.btn_install_cuda.setEnabled(False)
        self.btn_install_cuda.setText("Installing CUDA...")
        self.cuda_install_progress.setVisible(True)
        self.cuda_install_status.setVisible(True)
        self.cuda_install_progress.setValue(10)
        self.cuda_install_status.setText("Downloading CUDA packages from PyTorch repository...")

        self.cuda_worker = CudaInstallWorker()
        self.cuda_worker.progress.connect(self.cuda_install_progress.setValue)
        self.cuda_worker.status.connect(self.cuda_install_status.setText)

        def on_cuda_done(success, msg):
            self.btn_install_cuda.setEnabled(True)
            if success:
                self.btn_install_cuda.setText("Installed (Restart App)")
                self.cuda_install_status.setText("<span style='color: #48bb78; font-weight: bold;'>CUDA Installed! Please restart TinyLytic to activate RTX 3060 acceleration.</span>")
                QMessageBox.information(
                    self,
                    "CUDA Installation Complete",
                    "PyTorch CUDA acceleration has been installed successfully!\n\n"
                    "Please restart TinyLytic to enable full NVIDIA GeForce RTX 3060 GPU acceleration."
                )
            else:
                self.btn_install_cuda.setText("Retry CUDA Install")
                self.cuda_install_status.setText(f"Installation note: {msg}")
                QMessageBox.warning(self, "CUDA Installation Note", msg)

        self.cuda_worker.finished.connect(on_cuda_done)
        self.cuda_worker.start()

    def switchToSettingsTab(self):
        self.tabs.setCurrentWidget(self.tab_settings)

    def runBenchmark(self):
        specs = get_system_specs()
        msg = (
            f"Benchmark and Performance Profile\n\n"
            f"- Processor: {specs['cpu']}\n"
            f"- System Memory: {specs['ram_str']}\n"
            f"- Detected GPU: {specs['gpu_name']} ({specs['gpu_vram_gb']} GB VRAM)\n"
            f"- CUDA Accelerated: {'Yes (Active)' if specs['has_cuda'] else 'Available for RTX 3060 (Install via Settings)'}\n"
            f"- Hardware Recommendation: {specs['recommended_model_tier']}\n\n"
            f"TinyLytic settings are tuned for your system."
        )
        QMessageBox.information(self, "System Performance Profile", msg)

    # =========================================================================
    # ACTIVATION & LICENSING
    # =========================================================================
    def verifyLicenseKey(self, key):
        """Validate activation key against authorized keys, local file, and Gumroad API."""
        key = key.strip().upper()
        if not key:
            return False

        # 1. Check local key file (Activation Key.txt)
        local_key = ""
        key_file = resource_path("Activation Key.txt")
        if os.path.exists(key_file):
            try:
                with open(key_file, "r", encoding="utf-8") as f:
                    local_key = f.read().strip().upper()
            except Exception:
                pass

        clean_key = re.sub(r'[^A-Z0-9]', '', key)
        authorized_keys = [
            "6F0E4C97-B72A4E69-A11BF6C4-AF6517E7",
            "6F0E4C97B72A4E69A11BF6C4AF6517E7",
            "AIVORY2025ACTIVE",
            "TINYLYTIC-PRO-2025",
            "NOISHIXZEN-AIVORY-KEY"
        ]
        clean_authorized = [re.sub(r'[^A-Z0-9]', '', k) for k in authorized_keys]
        clean_local = re.sub(r'[^A-Z0-9]', '', local_key) if local_key else ""

        if key in authorized_keys or clean_key in clean_authorized or (clean_local and clean_key == clean_local):
            return True

        # 2. Gumroad Licensing API verification
        try:
            if requests:
                gumroad_endpoint = "https://api.gumroad.com/v2/licenses/verify"
                payload = {
                    "product_id": "Zvbao-lvFpatpUUC6HKwDg==",
                    "license_key": key
                }
                resp = requests.post(gumroad_endpoint, data=payload, timeout=6)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success") is True:
                        return True
        except Exception as g_err:
            print(f"[Gumroad Verify]: {g_err}")

        # 3. Fallback online verification
        if requests:
            try:
                resp = requests.get("https://raw.githubusercontent.com/pushpajit-dev/timelytic/main/activate.txt", timeout=4)
                if resp.status_code == 200 and resp.text.strip().upper() == key:
                    return True
            except Exception:
                pass

        return False

    def saveActivation(self, key):
        """Persist license information to LocalAppData and local flag."""
        try:
            lic_file = get_license_file_path()
            lic_data = {
                "activated": True,
                "license_key": key,
                "activated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "edition": "Pro Edition",
                "developer": "NoishiXzen & Aivory",
                "brand": "Aivory",
                "product_id": "Zvbao-lvFpatpUUC6HKwDg=="
            }
            with open(lic_file, "w", encoding="utf-8") as f:
                json.dump(lic_data, f, indent=2)
        except Exception as e:
            print(f"[License Save Error]: {e}")

        try:
            flag_path = resource_path("activated.flag")
            with open(flag_path, "w", encoding="utf-8") as f:
                f.write("true")
        except Exception:
            pass

    def showActivationDialog(self):
        """Show full license management dialog: view status, change key, activate or deactivate."""
        dlg = QDialog(self)
        dlg.setWindowTitle("TinyLytic Studio - License & Activation")
        dlg.resize(480, 320)
        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            dlg.setWindowIcon(QIcon(icon_path))
        vbox = QVBoxLayout(dlg)
        vbox.setSpacing(12)

        if self.is_activated:
            # -------------------------------------------------------------
            # ACTIVATED PRO VIEW
            # -------------------------------------------------------------
            header_box = QFrame()
            header_box.setStyleSheet("background-color: #1c4532; border: 1px solid #38a169; border-radius: 8px; padding: 12px;")
            h_layout = QVBoxLayout(header_box)
            h_title = QLabel("[PRO EDITION ACTIVATED]")
            h_title.setStyleSheet("color: #68d391; font-weight: bold; font-size: 13pt;")
            h_sub = QLabel("TinyLytic Studio Pro is activated. All features, AI Chat, Live Studio, Audio/Video Transcription, and Video Caption Studio are unlocked.")
            h_sub.setStyleSheet("color: #c6f6d5; font-size: 9pt;")
            h_sub.setWordWrap(True)
            h_layout.addWidget(h_title)
            h_layout.addWidget(h_sub)
            vbox.addWidget(header_box)

            info_form = QFormLayout()
            info_form.setSpacing(8)

            key_disp = self.activated_key or "6F0E4C97-B72A4E69-A11BF6C4-AF6517E7"
            key_row = QHBoxLayout()
            key_lbl = QLabel(f"<b>{key_disp}</b>")
            key_lbl.setStyleSheet("color: #63b3ed; font-size: 10pt;")
            key_row.addWidget(key_lbl, 1)

            btn_copy_key = QPushButton("Copy")
            btn_copy_key.setFixedWidth(60)
            btn_copy_key.clicked.connect(lambda: self.copyText(key_disp))
            key_row.addWidget(btn_copy_key)

            info_form.addRow("License Key:", key_row)
            info_form.addRow("License Status:", QLabel("Active (Lifetime Pro License)"))
            info_form.addRow("Product ID:", QLabel("Zvbao-lvFpatpUUC6HKwDg=="))
            info_form.addRow("Developer:", QLabel("NoishiXzen & Aivory"))
            info_form.addRow("Website:", QLabel("https://aivorygen.netlify.app"))
            vbox.addLayout(info_form)

            # Change Key Container (initially hidden)
            change_box = QFrame()
            change_box.setVisible(False)
            change_box.setStyleSheet("background-color: #1a202c; border: 1px solid #4a5568; border-radius: 6px; padding: 10px;")
            c_layout = QVBoxLayout(change_box)
            c_layout.addWidget(QLabel("<b>Enter New License Key:</b>"))
            new_key_input = QLineEdit()
            new_key_input.setPlaceholderText("Enter Gumroad or Product License Key...")
            c_layout.addWidget(new_key_input)
            c_status = QLabel("")
            c_status.setWordWrap(True)
            c_layout.addWidget(c_status)

            c_btn_row = QHBoxLayout()
            btn_apply_change = QPushButton("Validate & Update")
            btn_apply_change.setObjectName("actionBtn")
            c_btn_row.addWidget(btn_apply_change)
            btn_cancel_change = QPushButton("Cancel")
            c_btn_row.addWidget(btn_cancel_change)
            c_layout.addLayout(c_btn_row)
            vbox.addWidget(change_box)

            # Action button row
            btn_row = QHBoxLayout()
            btn_change = QPushButton("Change License Key")
            btn_change.clicked.connect(lambda: (change_box.setVisible(True), btn_row.setEnabled(False)))
            btn_row.addWidget(btn_change)

            btn_deact = QPushButton("Deactivate License")
            btn_deact.setStyleSheet("background-color: #742a2a; color: #ffffff; font-weight: bold;")
            def on_deactivate():
                reply = QMessageBox.question(
                    dlg, "Confirm Deactivation",
                    "Are you sure you want to deactivate TinyLytic Pro on this computer?\n\n"
                    "Pro features (AI Chat, Live Studio, Audio/Video Transcription, Caption Studio) will be locked.\n"
                    "YouTube Transcription will remain free forever.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        lic_file = get_license_file_path()
                        if os.path.exists(lic_file):
                            os.remove(lic_file)
                    except Exception:
                        pass
                    try:
                        flag_file = resource_path("activated.flag")
                        if os.path.exists(flag_file):
                            with open(flag_file, "w", encoding="utf-8") as f:
                                f.write("false")
                    except Exception:
                        pass
                    self.is_activated = False
                    self.activated_key = ""
                    self.applyActivationState()
                    QMessageBox.information(dlg, "Deactivated", "TinyLytic Pro has been deactivated.\nPro features are now locked.")
                    dlg.accept()

            btn_deact.clicked.connect(on_deactivate)
            btn_row.addWidget(btn_deact)

            btn_close = QPushButton("Close")
            btn_close.clicked.connect(dlg.accept)
            btn_row.addWidget(btn_close)
            vbox.addLayout(btn_row)

            def on_apply_new_key():
                k = new_key_input.text().strip().upper()
                if not k:
                    c_status.setText("<span style='color: #fc8181;'>Please enter a license key.</span>")
                    return
                c_status.setText("Validating license key...")
                QApplication.processEvents()
                if self.verifyLicenseKey(k):
                    self.saveActivation(k)
                    self.is_activated = True
                    self.activated_key = k
                    self.applyActivationState()
                    QMessageBox.information(dlg, "Activation Success", "License key successfully updated and activated!")
                    dlg.accept()
                else:
                    c_status.setText("<span style='color: #fc8181;'>Invalid license key. Please check your key.</span>")

            btn_apply_change.clicked.connect(on_apply_new_key)
            btn_cancel_change.clicked.connect(lambda: (change_box.setVisible(False), btn_row.setEnabled(True)))

        else:
            # -------------------------------------------------------------
            # UNACTIVATED FREE VIEW
            # -------------------------------------------------------------
            header_box = QFrame()
            header_box.setStyleSheet("background-color: #2d1515; border: 1px solid #e53e3e; border-radius: 8px; padding: 12px;")
            h_layout = QVBoxLayout(header_box)
            h_title = QLabel("[FREE EDITION - PRO LOCKED]")
            h_title.setStyleSheet("color: #fc8181; font-weight: bold; font-size: 13pt;")
            h_sub = QLabel("Enter your product license key to unlock AI Chat, Realtime Microphone Studio, Audio & Video Transcription, Video Caption Studio, and OCR Slide Detection.\n\nYouTube Transcription is 100% free forever.")
            h_sub.setStyleSheet("color: #fed7d7; font-size: 9pt;")
            h_sub.setWordWrap(True)
            h_layout.addWidget(h_title)
            h_layout.addWidget(h_sub)
            vbox.addWidget(header_box)

            vbox.addWidget(QLabel("<b>Enter Product Activation Key:</b>"))
            key_input = QLineEdit()
            key_input.setPlaceholderText("Enter Gumroad or Product License Key (e.g. 6F0E4C97-B72A4E69-A11BF6C4-AF6517E7)...")
            vbox.addWidget(key_input)

            status_lbl = QLabel("")
            status_lbl.setWordWrap(True)
            vbox.addWidget(status_lbl)

            btn_row = QHBoxLayout()
            btn_ok = QPushButton("Activate License")
            btn_ok.setObjectName("actionBtn")

            def on_activate():
                key = key_input.text().strip().upper()
                if not key:
                    status_lbl.setText("<span style='color: #fc8181;'>Please enter an activation key.</span>")
                    return

                status_lbl.setText("Verifying activation key...")
                QApplication.processEvents()

                if self.verifyLicenseKey(key):
                    self.saveActivation(key)
                    self.is_activated = True
                    self.activated_key = key
                    self.applyActivationState()
                    status_lbl.setText("<span style='color: #48bb78; font-weight: bold;'>Product Activated Successfully!</span>")
                    QMessageBox.information(dlg, "Activation Success", "TinyLytic Pro has been successfully activated!\nAll Pro features, Live Recording, and Video Caption Studio are now unlocked.")
                    dlg.accept()
                else:
                    status_lbl.setText("<span style='color: #fc8181;'>Invalid activation key. Please check your key or internet connection.</span>")

            btn_ok.clicked.connect(on_activate)
            btn_row.addWidget(btn_ok)

            btn_cancel = QPushButton("Cancel")
            btn_cancel.clicked.connect(dlg.reject)
            btn_row.addWidget(btn_cancel)

            vbox.addLayout(btn_row)

        dlg.exec()

    def showAboutDialog(self):
        msg = (
            "<h3>TinyLytic Studio v2.0</h3>"
            "<p><b>Developed by:</b> NoishiXzen &amp; Aivory<br>"
            "<b>Brand:</b> Aivory<br>"
            "<b>Official Website:</b> <a href='https://aivorygen.netlify.app' style='color: #63b3ed;'>https://aivorygen.netlify.app</a><br>"
            "<b>Support &amp; Inquiries:</b> <a href='mailto:noishixzen@gmail.com' style='color: #63b3ed;'>noishixzen@gmail.com</a></p>"
            "<hr style='border: 1px solid #2d3748;'>"
            "<p><b>Core Capabilities:</b></p>"
            "<ul>"
            "<li>OpenAI Whisper Multilingual Transcription across 35+ languages</li>"
            "<li>Bilingual Bengali + English Code-Switching &amp; Acoustic Multi-Speaker Diarization</li>"
            "<li>NVIDIA RTX CUDA Acceleration with automatic VRAM model matching</li>"
            "<li>Integrated Live Microphone Studio with volume monitor</li>"
            "<li>AI Chat Assistant for timestamped summarization and chaptering</li>"
            "<li>OpenCV &amp; OCR slide change detection</li>"
            "<li>Chapter Timestamps &amp; Clean Text export (TXT, SRT, VTT, JSON, CSV)</li>"
            "</ul>"
            "<p style='color: #a0aec0;'>Copyright &copy; 2026 NoishiXzen &amp; Aivory. All rights reserved.</p>"
        )
        QMessageBox.about(self, "Help", msg)

    def copyText(self, text):
        if text:
            pyperclip.copy(text)
            self.status_label.setText("Copied text to clipboard.")
        else:
            self.status_label.setText("Nothing to copy.")

    def exportCurrent(self, fmt):
        if not self.current_transcript_segments and not self.current_transcript_text:
            QMessageBox.warning(self, "No Transcript", "Please transcribe content first before exporting.")
            return

        filter_map = {
            "txt": "Text File with Timestamps (*.txt)",
            "clean": "Clean Reading Text File (*.txt)",
            "json": "JSON File (*.json)",
            "srt": "SubRip Subtitle (*.srt)",
            "vtt": "WebVTT Subtitle (*.vtt)",
            "csv": "CSV Spreadsheet (*.csv)"
        }
        path, _ = QFileDialog.getSaveFileName(self, f"Export Transcript as .{fmt.upper()}", f"transcript.{fmt}", filter_map.get(fmt, "All Files (*.*)"))
        if path:
            try:
                export_transcript(self.current_transcript_segments or self.current_transcript_text, format_type=fmt, file_path=path)
                QMessageBox.information(self, "Exported", f"Successfully exported to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def saveSession(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Session", "session_transcript.txt", "Text Files (*.txt)")
        if path and self.current_transcript_text:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.current_transcript_text)
            self.status_label.setText(f"Session saved to {os.path.basename(path)}")

    def loadSession(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Session", "", "Text Files (*.txt);;All Files (*.*)")
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.sendToChat(content)

    def clearTempCache(self):
        count = 0
        for f in glob.glob(os.path.join(TEMP_DIR, "*.*")):
            try:
                os.remove(f)
                count += 1
            except Exception:
                pass
        QMessageBox.information(self, "Clear", f"Cleared {count} temporary media files.")


def main():
    # Explicit Windows AppUserModelID ensures taskbar groups separately and displays app_icon.ico instead of python.exe
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("noishixzen.aivory.tinylytic.studio.v2")
    except Exception:
        pass

    app = QApplication(sys.argv)
    icon_path = resource_path("app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    app.setFont(QFont("Segoe UI", 10))
    window = TinyLyticApp()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
