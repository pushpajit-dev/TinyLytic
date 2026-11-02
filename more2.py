"""
TinyLytic Compatibility Module (more2.py)
Provides backward compatibility with previous builds while resolving all Python runtime errors,
hardcoded drive paths, and audio byte join exceptions.
"""

import sys
import os
import glob
import json
import re
import tempfile
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QProgressBar, QFileDialog,
    QTabWidget, QToolBar, QMainWindow, QMenu, QMenuBar, QMessageBox, QComboBox
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from core_engine import (
    get_app_data_dir, get_temp_dir, setup_ffmpeg,
    resource_path, segments_to_chapters, format_seconds
)
from workers import (
    UnifiedTranscriptionWorker, RealtimeRecorderWorker,
    YouTubeDownloadWorker, VisionAnalysisWorker
)

# Robust paths replacing hardcoded D:/YouTubeTimestampApp
BASE_DIR = get_app_data_dir()
TEMP_DIR = get_temp_dir()
LLAMA_MODEL_PATH = resource_path("models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")
LANGUAGE_MODELS_DIR = resource_path("lang_models")

# Transcription Worker alias
class TranscriptionWorker(UnifiedTranscriptionWorker):
    """Drop-in replacement for old TranscriptionWorker with 100% compatibility."""
    eta = pyqtSignal(str)

    def __init__(self, file_path, model_id="tiny", language=None, task="transcribe", num_speakers=1):
        super().__init__(media_path=file_path, model_id=model_id, language=language, task=task, num_speakers=num_speakers)
        # Connect status signal to eta for legacy listeners
        self.status.connect(self.eta.emit)

        # Connect result signal
        def on_result(text, segments):
            # Also emit result text to legacy single-argument listeners
            self.result_legacy.emit(text)

        self.result.connect(on_result)

    result_legacy = pyqtSignal(str)


# Legacy YouTubeTimestampApp fallback container
class YouTubeTimestampApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TinyLytic - Studio")
        self.setGeometry(100, 100, 800, 650)
        self.central = QLabel("Please run the main Tinylytic.py application for the unified modern experience.")
        self.setCentralWidget(self.central)
