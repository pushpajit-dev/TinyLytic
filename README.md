<div align="center">


# TinyLytic Studio

### Next-Generation Speech Intelligence, Video Captioning, and Multimodal Analytics Suite

[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue.svg?style=flat-square)](https://microsoft.com/windows)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square)](https://python.org)
[![Framework: PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg?style=flat-square)](https://riverbankcomputing.com/software/pyqt)
[![Engine: Whisper](https://img.shields.io/badge/ASR-OpenAI%20Whisper-orange.svg?style=flat-square)](https://github.com/openai/whisper)
[![Hardware: CUDA Ready](https://img.shields.io/badge/Acceleration-NVIDIA%20CUDA-76B900.svg?style=flat-square)](https://developer.nvidia.com/cuda-zone)
[![License: Commercial / Free Tier](https://img.shields.io/badge/License-Commercial%20%2F%20Free%20Tier-lightgrey.svg?style=flat-square)](#licensing-and-activation)

<br>

<p align="center">
  <a href="https://drive.google.com/file/d/19dMnY4dcWLEKgbB3afHXkKa8XyAUBFcJ/view?usp=sharing">
    <img src="https://img.shields.io/badge/DOWNLOAD-TinyLytic%20Setup%20v2.0%20(EXE)-2b6cb0?style=for-the-badge&logo=windows&logoColor=white" alt="Download TinyLytic Installer">
  </a>
</p>

<p align="center">
  <b>Direct Installer Link:</b> <a href="https://drive.google.com/file/d/19dMnY4dcWLEKgbB3afHXkKa8XyAUBFcJ/view?usp=sharing">Download TinyLytic_Setup_v2.0.exe</a>
</p>

<br>

<img src="https://i.imgur.com/CEr6eMl.jpeg" alt="Gemini_Generated_Image_7hk7rg7hk7rg7hk7-clean" width="100%">

</div>

---

## Overview

TinyLytic Studio is a comprehensive, standalone desktop application built for content creators, transcribers, researchers, and developers. It unifies state-of-the-art speech-to-text recognition, dynamic multilingual code-switching, professional word-level video captioning with typography styling, an interactive local AI chat assistant, and slide vision recognition into a single high-performance package.

TinyLytic Studio runs completely locally on your hardware. It offers full offline neural inference without external API fees, telemetry, or cloud dependency.

---

## Core Capabilities

### 1. YouTube Transcription (100% Free Forever)
- Multi-tier stream extraction engine utilizing native `yt-dlp` and embedded FFmpeg.
- Resilient client fallback architecture (`iOS`, `Android`, `TV Embedded`, `Mobile Web`) designed to bypass automated bot detection and sign-in constraints.
- Real-time download progress tracking with direct audio extraction into high-precision 16 kHz streams.
- One-click YouTube chapter timestamp generation, transcript clean-up, and formatted description exports.

### 2. Live Realtime Microphone Recording Studio
- Direct hardware enumeration with low-latency Windows WASAPI drivers, completely isolating unstable WDM-KS ports.
- Multi-channel downmixing (`np.mean(indata, axis=1)`) ensuring compatibility across stereo USB microphones (e.g. Owl Lite, Blue Yeti, Logitech, Realtek).
- Studio-grade acoustic vocal processing: automatic DC offset removal, dynamic peak volume normalization, and silence trimming.
- Real-time audio volume visualizer and elapsed time tracking.

### 3. Multilingual and Code-Switching Transcription
- Dynamic per-window language detection designed for mixed bilingual speech (such as English and Bengali).
- Context-guided initial prompting: ensures both English terms and Bengali script are transcribed in their native alphabets without phonetic corruption.
- Full support for native punctuation: Bengali দাঁড়ি (`।`), কমা (`,`), question marks, and English punctuation marks.
- Speaker diarization for multi-speaker conversations (`Auto Detect` or 2 to 10 speaker tracking).

### 4. Video Caption Studio
- Interactive video canvas with synchronized audio playback powered by `PyQt6.QtMultimedia` (`QMediaPlayer` and `QAudioOutput`).
- Integrated playback volume slider (`Vol: 0-100%`) with automatic audio scrubbing, pause, resume, and loop resets.
- Asynchronous PCM WAV extraction fallback for non-standard video formats (WebM, MKV, AVI, MOV).
- Word-by-word synchronized caption animation presets:
  - Pop Animation
  - Smooth Fade In / Out
  - Slide Transition
  - Jump Emphasis
  - Dynamic Color Outline
  - Cinematic Motion Blur
- Professional typography controls: font family, font size, line spacing / paragraph gap, vertical offset, text color, outline stroke, and drop shadow.
- Multi-format export pipeline:
  - High-bitrate MP4 with audio remuxing
  - Green Screen background replacement (for video editing overlays)
  - Transparent MOV (Apple ProRes 4444 / PNG codec)
  - Full transparent PNG frame sequence bundled into a ZIP archive

### 5. Interactive AI Chat Assistant
- Permanently unlocked for all users without license restrictions.
- Proactive background companion: automatically invites you into conversation when a transcription task starts, offering engaging icebreakers from an integrated 50-question collection.
- Conversational name memory and polite dialogue on science, engineering, philosophy, programming, and general knowledge.
- Multi-backend architecture:
  - Built-in Intelligent Assistant (instant zero-ram rule-based reasoning engine)
  - Local Ollama Integration (`http://127.0.0.1:11434`) with automated model detection
  - Local TinyLLaMA GGUF inference via `llama-cpp-python`
- Quick actions: Summarize Transcript, Extract Key Points, Format Chapters, and Analyze Tone.

### 6. Vision and Slide OCR Analytics
- Video keyframe and slide transition extractor powered by OpenCV.
- Optical Character Recognition (OCR) integration via Tesseract for automated text extraction from video slides, diagrams, and screen recordings.

### 7. Diagnostics and Hardware Acceleration
- Hardware auto-detection: CPU architecture, system RAM, detected NVIDIA GPU, dedicated VRAM, driver version, and CUDA toolkit status.
- One-click PyTorch CUDA acceleration installer.
- Live background process terminal stream viewable directly within the Settings tab.
- Integrated `yt-dlp` package updater to maintain compatibility against upstream changes.

---

## Download and Installation

### Official Downloads

| Package Type | Architecture | File Size | Download |
| :--- | :--- | :--- | :--- |
| **Windows Full Setup (.exe)** | Windows 64-bit | ~2.11 GB | [Download via Google Drive](https://drive.google.com/file/d/19dMnY4dcWLEKgbB3afHXkKa8XyAUBFcJ/view?usp=sharing) |
| **Standalone MSI Installer (.msi)** | Windows 64-bit | ~1.81 MB | Found in `Installers_Output\TinyLytic_Setup_v2.0.msi` |

### Method 1: Windows Executable Setup (Recommended)
1. Download `TinyLytic_Setup_v2.0.exe` from the link above.
2. Double-click the installer and follow the setup wizard.
3. The setup package automatically installs:
   - TinyLytic Studio core runtime
   - Embedded Whisper models (`tiny.pt`, `whisper-medium.pt`)
   - Local TinyLLaMA model (`tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`)
   - High-resolution application shortcuts and uninstaller
4. Launch **TinyLytic Studio** from your Start Menu or Desktop shortcut.

### Method 2: Standalone MSI Package
For enterprise or scripted network deployment:
```cmd
msiexec /i TinyLytic_Setup_v2.0.msi /qn
```

### Method 3: Running from Source
If running in a developer environment:
1. Clone this repository or extract the project files:
   ```cmd
   cd "TinyLytic"
   ```
2. Create and activate a Python virtual environment:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install required dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
4. Start the application:
   ```cmd
   python Tinylytic.py
   ```

---

## System Requirements

| Component | Minimum Specification | Recommended Specification |
| :--- | :--- | :--- |
| **Operating System** | Windows 10 (64-bit) Build 19041+ | Windows 11 (64-bit) Latest Build |
| **Processor** | Intel Core i3 (8th Gen) or AMD Ryzen 3 | Intel Core i7 / AMD Ryzen 7 or higher |
| **Memory** | 8 GB RAM | 16 GB RAM or higher |
| **Graphics** | Integrated Graphics | NVIDIA GeForce RTX Series (6 GB+ VRAM) |
| **Storage** | 4 GB free disk space (SSD) | 10 GB free disk space (NVMe SSD) |
| **Audio** | Standard Windows Microphone | Dedicated USB Condenser Microphone |

---

## Licensing and Activation

TinyLytic Studio is distributed with a **Tiered Commercial License**:

- **Free Tier (Lifetime Unlocked)**:
  - YouTube Audio and Video Transcription
  - Subtitle Generation and YouTube Chapters Formatting
  - Full AI Chat Assistant (Built-in, Ollama, TinyLLaMA)
  - Hardware Diagnostics and Terminal Diagnostics
- **Pro Tier (Commercial License)**:
  - Live Realtime Microphone Recording Studio
  - Local Audio File Transcription (WAV, MP3, FLAC, M4A, OGG)
  - Local Video File Transcription (MP4, MKV, MOV, WebM, AVI)
  - Video Caption Studio (Animations, Typography, Green Screen, Transparent MOV/ZIP Export)
  - Slide Vision OCR Analytics

### License Verification
- **Product ID**: `Zvbao-lvFpatpUUC6HKwDg==`
- **Official Test / Demo Key**: `6F0E4C97-B72A4E69-A11BF6C4-AF6517E7`

To activate TinyLytic Pro:
1. Navigate to the **Settings** tab or click **Activation** in the top menu bar.
2. Enter your product key and click **Activate**.
3. Once validated, all Pro modules are unlocked immediately.

---

## Credits and Brand Attribution

TinyLytic Studio is designed and maintained by:

- **Lead Developers**: NoishiXzen and Aivory
- **Brand**: Aivory / Kupido
- **Official Website**: [https://aivorygen.netlify.app](https://aivorygen.netlify.app)
- **Technical Support & Inquiries**: [noishixzen@gmail.com](mailto:noishixzen@gmail.com)

### Open Source Acknowledgments
TinyLytic Studio incorporates technologies from the following open-source projects:
- [OpenAI Whisper](https://github.com/openai/whisper) - Robust Speech Recognition via Large-Scale Weak Supervision
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI Application Framework
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Media Stream Extraction Utility
- [FFmpeg](https://ffmpeg.org/) - Hyper-fast Audio and Video Processing
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) - Local GGUF LLM Inference
- [SoundDevice](https://python-sounddevice.readthedocs.io/) & [SoundFile](https://pysoundfile.readthedocs.io/) - Real-time Audio I/O

---

<div align="center">
  <sub>Copyright &copy; 2026 NoishiXzen &amp; Aivory. All rights reserved.</sub>
</div>
