"""
TinyLytic Core Engine
High-performance backend services for audio/video transcription, realtime recording,
computer vision (CV2/OCR), and AI chat assistant.
"""

import os
import sys
import tempfile
import json
import re
import glob
import time
import subprocess
import platform
from datetime import datetime

# Safe path helper
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller/cx_Freeze."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def get_app_data_dir():
    """Get a safe, writable application directory."""
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        app_dir = os.path.join(base, "TinyLytic")
    else:
        app_dir = os.path.join(os.path.expanduser("~"), ".tinylytic")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

def get_temp_dir():
    """Get a safe temporary directory for media processing."""
    temp_dir = os.path.join(tempfile.gettempdir(), "TinyLytic_Temp")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

# Global paths
BASE_DIR = get_app_data_dir()
TEMP_DIR = get_temp_dir()

# FFmpeg Discovery and Path Injection
import shutil

def setup_ffmpeg():
    """Ensure ffmpeg is in PATH by checking system PATH, WinGet, imageio_ffmpeg, or local folders."""
    # 1. Check system PATH via shutil.which for full path
    p = shutil.which("ffmpeg")
    if p and os.path.isfile(p):
        full_path = os.path.abspath(p)
        ffmpeg_dir = os.path.dirname(full_path)
        if ffmpeg_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        return full_path

    # 2. Check imageio_ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(ffmpeg_exe):
            full_path = os.path.abspath(ffmpeg_exe)
            ffmpeg_dir = os.path.dirname(full_path)
            if ffmpeg_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
            return full_path
    except Exception:
        pass

    # 3. Check WinGet Packages and local directories
    local_candidates = [
        os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages"),
        resource_path("lib/imageio_ffmpeg/binaries"),
        resource_path("bin"),
        resource_path("assets"),
        os.path.join(os.path.dirname(sys.executable), "lib/imageio_ffmpeg/binaries"),
        os.path.join(os.path.dirname(sys.executable), "bin"),
        "C:\\ffmpeg\\bin",
        "C:\\Program Files\\ffmpeg\\bin",
    ]
    for cand in local_candidates:
        if os.path.isdir(cand):
            for root, dirs, files in os.walk(cand):
                for file in files:
                    if file.lower() == "ffmpeg.exe":
                        full_path = os.path.abspath(os.path.join(root, file))
                        root_abs = os.path.abspath(root)
                        if root_abs not in os.environ.get("PATH", ""):
                            os.environ["PATH"] = root_abs + os.pathsep + os.environ.get("PATH", "")
                        return full_path

    return None

FFMPEG_PATH = setup_ffmpeg()

# Clean Processor Detection
def get_clean_cpu_name():
    """Detect clean processor marketing name and remove raw architecture/GenuineIntel strings."""
    cpu_name = ""
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except Exception:
            pass

    if not cpu_name:
        cpu_name = platform.processor() or "Processor"

    # Thoroughly strip noise like GenuineIntel, (R), (TM), CPU @ 2.80GHz, Stepping, Family
    noise_patterns = [
        r"GenuineIntel",
        r"AuthenticAMD",
        r"\(R\)",
        r"\(TM\)",
        r",\s*Family\s*\d+\s*Model\s*\d+\s*Stepping\s*\d+",
        r"\s*CPU\s*@\s*[\d\.]+\s*GHz",
        r"\s*@\s*[\d\.]+\s*GHz"
    ]
    for pat in noise_patterns:
        cpu_name = re.sub(pat, "", cpu_name, flags=re.IGNORECASE)

    # Normalize spaces
    cpu_name = re.sub(r"\s+", " ", cpu_name).strip()

    # Append physical core count if available
    try:
        import psutil
        cores = psutil.cpu_count(logical=False)
        threads = psutil.cpu_count(logical=True)
        if cores and threads:
            cpu_name = f"{cpu_name} ({cores} Cores, {threads} Threads)"
    except Exception:
        pass

    return cpu_name or "Intel / AMD Processor"

# Hardware & System Specs
def get_system_specs():
    """Query CPU, RAM, and GPU capabilities with CUDA support detection."""
    clean_cpu = get_clean_cpu_name()
    specs = {
        "cpu": clean_cpu,
        "ram_gb": 0,
        "ram_str": "Unknown",
        "gpu_name": "No GPU detected",
        "gpu_vram_mb": 0,
        "gpu_vram_gb": 0.0,
        "has_cuda": False,
        "cuda_capable": False,
        "cuda_version": None,
        "driver_version": None,
        "gpus": [],
        "recommended_device": "cpu",
        "recommended_model_tier": "Tiny or Base (CPU Mode)",
        "available_devices": []
    }

    # 1. Total System RAM
    try:
        import psutil
        ram = psutil.virtual_memory().total / (1024 ** 3)
        specs["ram_gb"] = round(ram, 1)
        specs["ram_str"] = f"{specs['ram_gb']} GB"
    except Exception:
        pass

    # 2. Detect PyTorch CUDA status
    try:
        import torch
        if torch.cuda.is_available():
            specs["has_cuda"] = True
            specs["cuda_version"] = torch.version.cuda
            specs["recommended_device"] = "cuda"
            for i in range(torch.cuda.device_count()):
                dev_name = torch.cuda.get_device_name(i)
                dev_mem_mb = round(torch.cuda.get_device_properties(i).total_memory / (1024 ** 2))
                dev_mem_gb = round(dev_mem_mb / 1024, 1)
                specs["gpus"].append({
                    "id": i,
                    "name": dev_name,
                    "vram_mb": dev_mem_mb,
                    "vram_gb": dev_mem_gb
                })
    except Exception:
        pass

    # 4. Fallback physical GPU query via nvidia-smi / GPUtil
    if not specs["gpus"]:
        try:
            import subprocess
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3
            )
            if res.returncode == 0:
                specs["cuda_capable"] = True
                for idx, line in enumerate(res.stdout.strip().splitlines()):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 3:
                        v_mb = int(float(parts[1]))
                        specs["gpus"].append({
                            "id": idx,
                            "name": parts[0],
                            "vram_mb": v_mb,
                            "vram_gb": round(v_mb / 1024, 1),
                            "driver": parts[2]
                        })
                        specs["driver_version"] = parts[2]
        except Exception:
            pass

    if not specs["gpus"]:
        try:
            import GPUtil
            for idx, g in enumerate(GPUtil.getGPUs()):
                specs["cuda_capable"] = True
                specs["gpus"].append({
                    "id": idx,
                    "name": g.name,
                    "vram_mb": int(g.memoryTotal),
                    "vram_gb": round(g.memoryTotal / 1024, 1)
                })
        except Exception:
            pass

    # Summarize Primary GPU
    if specs["gpus"]:
        primary_gpu = specs["gpus"][0]
        specs["gpu_name"] = primary_gpu["name"]
        specs["gpu_vram_mb"] = primary_gpu["vram_mb"]
        specs["gpu_vram_gb"] = primary_gpu["vram_gb"]
        if specs["has_cuda"]:
            specs["recommended_device"] = "cuda"
        else:
            specs["cuda_capable"] = True

    # 5. Model Tier Recommendation based on VRAM
    vram = specs["gpu_vram_gb"]
    if vram >= 10.0:
        specs["recommended_model_tier"] = "Large-v3 or Recommended (12 GB VRAM supports all models at peak speed)"
    elif vram >= 5.0:
        specs["recommended_model_tier"] = "Recommended (Medium) or Small"
    elif vram >= 2.0:
        specs["recommended_model_tier"] = "Small or Base"
    else:
        specs["recommended_model_tier"] = "Tiny or Base (Fast execution on CPU)"

    # 6. Available Compute Devices
    devices = [{"id": "auto", "name": "Auto (Fastest Available)"}]
    if specs["has_cuda"]:
        for g in specs["gpus"]:
            devices.append({
                "id": f"cuda:{g['id']}",
                "name": f"CUDA: {g['name']} ({g['vram_gb']} GB VRAM)"
            })
        if len(specs["gpus"]) > 1:
            devices.append({"id": "multi_gpu", "name": "Multi-GPU: All GPUs Together"})
        devices.append({"id": "hybrid", "name": "Both: GPU + CPU (Hybrid Acceleration)"})
    elif specs["cuda_capable"]:
        devices.append({
            "id": "cuda:0",
            "name": f"CUDA: {specs['gpu_name']} ({specs['gpu_vram_gb']} GB VRAM - Setup Available)"
        })
        devices.append({"id": "hybrid", "name": "Both: GPU + CPU (Hybrid Acceleration)"})

    short_cpu = clean_cpu.split("@")[0].strip() if "@" in clean_cpu else clean_cpu[:30]
    devices.append({"id": "cpu", "name": f"CPU: Multi-threaded ({short_cpu})"})
    specs["available_devices"] = devices

    return specs

# Whisper Official Download Models Catalog
WHISPER_DOWNLOAD_CATALOG = {
    "medium": {
        "name": "Recommended",
        "filename": "whisper-medium.pt",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
        "size_str": "1.5 GB",
        "vram_req": "~5 GB VRAM",
        "desc": "High accuracy multilingual model. Recommended for RTX 3060."
    },
    "tiny": {
        "name": "Tiny",
        "filename": "tiny.pt",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt",
        "size_str": "75 MB",
        "vram_req": "<1 GB VRAM / CPU",
        "desc": "Ultra-fast lightweight model for quick transcriptions."
    },
    "base": {
        "name": "Base",
        "filename": "base.pt",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt",
        "size_str": "142 MB",
        "vram_req": "~1 GB VRAM / CPU",
        "desc": "Fast balanced model for clean speech."
    },
    "small": {
        "name": "Small",
        "filename": "small.pt",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt",
        "size_str": "466 MB",
        "vram_req": "~2 GB VRAM",
        "desc": "Enhanced multilingual accuracy with moderate footprint."
    },
    "large-v3": {
        "name": "Large-v3",
        "filename": "large-v3.pt",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt",
        "size_str": "2.9 GB",
        "vram_req": "~10 GB VRAM",
        "desc": "State-of-the-art accuracy. Supported on your RTX 3060."
    }
}

# Whisper Models Discovery
def get_available_whisper_models():
    """Find locally bundled Whisper models and standard sizes with Recommended selection."""
    models_dir = resource_path("models")
    models = []

    # Check local models
    if os.path.exists(models_dir):
        for f in os.listdir(models_dir):
            if f.endswith(".pt"):
                full_path = os.path.join(models_dir, f)
                f_lower = f.lower()
                if "medium" in f_lower:
                    # Clean Recommended name
                    models.insert(0, {
                        "name": "Recommended",
                        "id": full_path,
                        "is_local": True
                    })
                elif "tiny" in f_lower:
                    models.append({
                        "name": "Tiny",
                        "id": full_path,
                        "is_local": True
                    })
                elif "base" in f_lower:
                    models.append({
                        "name": "Base",
                        "id": full_path,
                        "is_local": True
                    })
                elif "small" in f_lower:
                    models.append({
                        "name": "Small",
                        "id": full_path,
                        "is_local": True
                    })
                elif "large" in f_lower:
                    models.append({
                        "name": "Large-v3",
                        "id": full_path,
                        "is_local": True
                    })
                else:
                    models.append({
                        "name": f.replace(".pt", "").capitalize(),
                        "id": full_path,
                        "is_local": True
                    })

    # Standard online/cached models
    standard_models = [
        {"name": "Tiny", "id": "tiny", "is_local": False},
        {"name": "Base", "id": "base", "is_local": False},
        {"name": "Small", "id": "small", "is_local": False},
        {"name": "Large-v3", "id": "large-v3", "is_local": False},
    ]

    for m in standard_models:
        if not any(m["name"].lower() == existing["name"].lower() for existing in models):
            models.append(m)

    # Ensure Recommended is first if present
    rec_idx = next((i for i, item in enumerate(models) if item["name"] == "Recommended"), -1)
    if rec_idx > 0:
        rec_item = models.pop(rec_idx)
        models.insert(0, rec_item)

    return models

# Supported Languages for Whisper
SUPPORTED_LANGUAGES = {
    "Auto Lang": None,
    "Multilang": "multilang",
    "Bengali (বাংলা)": "bn",
    "English": "en",
    "Hindi (हिन्दी)": "hi",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Chinese": "zh",
    "Japanese": "ja",
    "Korean": "ko",
    "Arabic": "ar",
    "Turkish": "tr",
    "Dutch": "nl",
    "Polish": "pl",
    "Indonesian": "id",
    "Vietnamese": "vi",
    "Ukrainian": "uk",
    "Swedish": "sv",
    "Greek": "el",
    "Czech": "cs",
    "Romanian": "ro",
    "Danish": "da",
    "Finnish": "fi",
    "Hungarian": "hu",
    "Tamil": "ta",
    "Telugu": "te",
    "Marathi": "mr",
    "Urdu": "ur",
    "Gujarati": "gu",
    "Malayalam": "ml",
    "Kannada": "kn",
    "Punjabi": "pa"
}

def detect_segment_language(text):
    """Detect dominant language or bilingual code-switching (Hinglish, Bengali+English, etc.) in a text segment."""
    if not text:
        return "English"

    bn_count = sum(1 for c in text if '\u0980' <= c <= '\u09FF')
    hi_count = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    en_count = sum(1 for c in text if 'a' <= c.lower() <= 'z')

    # Detect Latin-script code-switching (Hinglish / Romanized Bengali)
    words_lower = set(re.findall(r'\b[a-z]{3,}\b', text.lower()))
    hinglish_markers = {"hai", "hote", "karna", "karo", "mera", "meri", "kya", "nahi", "kyun", "bhai", "theek", "accha", "aaj", "hum", "aap", "tum", "kaise", "sab"}
    bangla_lat_markers = {"ami", "tumi", "apni", "kemon", "bhalo", "korchi", "korbo", "hobe", "achho", "shob", "kono", "khobor"}

    has_hinglish_words = len(words_lower.intersection(hinglish_markers)) >= 2
    has_bangla_words = len(words_lower.intersection(bangla_lat_markers)) >= 2

    if bn_count >= 2 and en_count >= 3:
        return "Bengali+English"
    elif hi_count >= 2 and en_count >= 3:
        return "Hinglish"
    elif has_hinglish_words:
        return "Hinglish"
    elif has_bangla_words:
        return "Bengali+English"
    elif bn_count > en_count and bn_count > hi_count:
        return "Bengali"
    elif hi_count > en_count and hi_count > bn_count:
        return "Hindi"
    elif en_count > 0:
        return "English"
    return "English"

def format_multilingual_punctuation(text, lang=None):
    """
    Format punctuation marks appropriately for multilingual scripts:
    - Replaces trailing '.' with Bengali dā̃ṛi '।' when text is in Bengali script.
    - Preserves and formats commas ',', question marks '?', exclamation marks '!'.
    - Formats Devanagari/Hindi with '।'.
    """
    if not text:
        return text

    # Check for Bengali script (\u0980-\u09FF)
    has_bengali = any('\u0980' <= c <= '\u09FF' for c in text)
    has_hindi = any('\u0900' <= c <= '\u097F' for c in text)

    if has_bengali:
        # Replace trailing periods with Bengali dā̃ṛi '।'
        text = re.sub(r'\.\s*$', '।', text)
        text = re.sub(r'\.\s+', '। ', text)
        # Ensure clean spacing around punctuation
        text = re.sub(r'\s*।\s*', '। ', text)
        text = re.sub(r'\s*,\s*', ', ', text)
        text = re.sub(r'\s*\?\s*', '? ', text)
        text = re.sub(r'\s*!\s*', '! ', text)
    elif has_hindi:
        text = re.sub(r'\.\s*$', '।', text)
        text = re.sub(r'\.\s+', '। ', text)
        text = re.sub(r'\s*।\s*', '। ', text)
        text = re.sub(r'\s*,\s*', ', ', text)
    else:
        # Standard clean spacing for English and other scripts
        text = re.sub(r'\s*,\s*', ', ', text)
        text = re.sub(r'\s*\.\s*', '. ', text)

    return text.strip()

def perform_speaker_diarization(audio_path, segments, num_speakers="auto"):
    """
    Cluster Whisper segments into distinct speakers using acoustic voice features (pitch, centroid, timbre).
    Supports automatic speaker count detection ('auto') using acoustic variance clustering.
    """
    if not segments:
        return segments

    try:
        import soundfile as sf
        import numpy as np

        data, sr = sf.read(audio_path, always_2d=True)
        mono = np.mean(data, axis=1)

        if sr != 16000:
            step = max(1, int(sr / 16000))
            mono = mono[::step]
            sr = 16000

        embeddings = []
        for seg in segments:
            start_idx = int(seg.get("start", 0) * sr)
            end_idx = int(seg.get("end", 0) * sr)
            chunk = mono[start_idx:end_idx]

            if len(chunk) < int(sr * 0.15):
                embeddings.append(np.zeros(8))
                continue

            # 1. Energy
            rms = float(np.sqrt(np.mean(chunk ** 2) + 1e-12))
            # 2. ZCR
            zcr = float(np.mean(np.abs(np.diff(np.sign(chunk)))) / 2.0)
            # 3. FFT Spectrum
            fft = np.abs(np.fft.rfft(chunk))
            freqs = np.fft.rfftfreq(len(chunk), 1.0 / sr)
            sum_fft = float(np.sum(fft) + 1e-12)
            # 4. Spectral Centroid
            centroid = float(np.sum(freqs * fft) / sum_fft)
            # 5. Spectral Spread
            spread = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * fft) / sum_fft))
            # 6. Sub-band frequency energies
            b1 = float(np.sum(fft[(freqs >= 50) & (freqs < 300)]) / sum_fft)
            b2 = float(np.sum(fft[(freqs >= 300) & (freqs < 1200)]) / sum_fft)
            b3 = float(np.sum(fft[(freqs >= 1200) & (freqs < 3500)]) / sum_fft)
            # 7. Fast Pitch Autocorrelation (Windowed 2048 samples, < 1ms)
            if len(chunk) > 2048:
                mid = len(chunk) // 2
                slice_chunk = chunk[mid - 1024 : mid + 1024]
            else:
                slice_chunk = chunk

            slice_chunk = slice_chunk - np.mean(slice_chunk)
            corr = np.correlate(slice_chunk, slice_chunk, mode='full')
            corr = corr[len(corr)//2:]
            lag_min = int(sr / 400)
            lag_max = min(int(sr / 80), len(corr) - 1)
            if lag_max > lag_min:
                pitch_lag = lag_min + np.argmax(corr[lag_min:lag_max])
                pitch_hz = float(sr / (pitch_lag + 1e-5))
            else:
                pitch_hz = 150.0

            feat = np.array([rms, zcr, centroid / 4000.0, spread / 2000.0, b1, b2, b3, pitch_hz / 300.0])
            embeddings.append(feat)

        embeddings = np.array(embeddings)
        if len(embeddings) < 2:
            for s in segments:
                s["speaker"] = "Speaker 1"
            return segments

        # Determine speaker count automatically if requested
        if num_speakers in ("auto", "Auto", 0, None):
            emb_std = np.std(embeddings, axis=0)
            pitch_std = emb_std[7]
            spec_std = emb_std[2]
            if pitch_std > 0.18 or spec_std > 0.16:
                actual_k = 2
                if len(embeddings) >= 8 and (pitch_std > 0.32 or spec_std > 0.28):
                    actual_k = 3
            else:
                actual_k = 1
        else:
            try:
                actual_k = max(1, int(num_speakers))
            except Exception:
                actual_k = 2

        if actual_k <= 1 or len(embeddings) < actual_k:
            for s in segments:
                s["speaker"] = "Speaker 1"
            return segments

        norm_emb = (embeddings - np.mean(embeddings, axis=0)) / (np.std(embeddings, axis=0) + 1e-6)

        np.random.seed(42)
        centroids = norm_emb[np.random.choice(len(norm_emb), actual_k, replace=False)].copy()
        labels = np.zeros(len(norm_emb), dtype=int)
        for _ in range(15):
            dists = np.linalg.norm(norm_emb[:, np.newaxis] - centroids, axis=2)
            labels = np.argmin(dists, axis=1)
            for k in range(actual_k):
                if np.any(labels == k):
                    centroids[k] = np.mean(norm_emb[labels == k], axis=0)

        for idx, s in enumerate(segments):
            s["speaker"] = f"Speaker {labels[idx] + 1}"

    except Exception as e:
        print(f"[Diarization Notice]: {e}")
        for s in segments:
            s["speaker"] = "Speaker 1"

    return segments

# Timestamp Formatting Helper
def format_seconds(seconds):
    """Format seconds into HH:MM:SS or MM:SS."""
    seconds = int(round(seconds))
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if hrs > 0:
        return f"{hrs:02}:{mins:02}:{secs:02}"
    return f"{mins:02}:{secs:02}"

def segments_to_chapters(segments, max_chunk_len=120, include_speaker=True, include_lang=True):
    """Convert Whisper segments into clean chapter timestamps with speaker & language labels."""
    chapters = []
    chapter_num = 1
    current_start = None
    current_end = None
    current_texts = []
    current_speaker = None
    current_lang = None

    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        raw_text = seg.get("text", "").strip()
        speaker = seg.get("speaker", "Speaker 1")
        lang = seg.get("language") or detect_segment_language(raw_text)
        text = format_multilingual_punctuation(raw_text, lang)
        seg["language"] = lang
        seg["text"] = text

        if not text:
            continue

        # If speaker changed, flush current chapter
        if current_start is not None and include_speaker and current_speaker != speaker:
            time_str = f"{format_seconds(current_start)}-{format_seconds(current_end)}"
            tag = f"[{current_speaker} | {current_lang}]" if (include_speaker and include_lang) else (f"[{current_speaker}]" if include_speaker else "")
            chapters.append(f"{time_str} {tag} Chapter {chapter_num}: {' '.join(current_texts)}")
            chapter_num += 1
            current_start = None
            current_texts = []

        if current_start is None:
            current_start = start
            current_speaker = speaker
            current_lang = lang

        current_end = end
        current_texts.append(text)

        combined_text = " ".join(current_texts)
        if len(combined_text) >= max_chunk_len:
            time_str = f"{format_seconds(current_start)}-{format_seconds(current_end)}"
            tag = f"[{current_speaker} | {current_lang}]" if (include_speaker and include_lang) else (f"[{current_speaker}]" if include_speaker else "")
            chapters.append(f"{time_str} {tag} Chapter {chapter_num}: {combined_text}")
            chapter_num += 1
            current_start = None
            current_texts = []

    if current_texts and current_start is not None:
        time_str = f"{format_seconds(current_start)}-{format_seconds(current_end)}"
        tag = f"[{current_speaker} | {current_lang}]" if (include_speaker and include_lang) else (f"[{current_speaker}]" if include_speaker else "")
        chapters.append(f"{time_str} {tag} Chapter {chapter_num}: {' '.join(current_texts)}")

    return "\n".join(chapters)

def clean_transcript_text(text_or_segments):
    """Convert formatted chapters or segments into pure, clean, flowing paragraphs without timestamps or tags."""
    if not text_or_segments:
        return ""

    import re

    # If segment list is passed
    if isinstance(text_or_segments, list):
        paragraphs = []
        current_para = []
        current_speaker = None
        current_char_count = 0

        for seg in text_or_segments:
            if not isinstance(seg, dict):
                continue
            txt = format_multilingual_punctuation(seg.get("text", "").strip(), seg.get("language"))
            if not txt:
                continue
            spk = seg.get("speaker")

            # Break into paragraph if speaker changes or after reaching sufficient length with punctuation
            is_punct_end = txt.endswith(('.', '!', '?', '।', ':', ';'))
            if (current_speaker is not None and spk != current_speaker and current_para) or \
               (current_char_count >= 350 and is_punct_end):
                paragraphs.append(" ".join(current_para))
                current_para = [txt]
                current_char_count = len(txt)
            else:
                current_para.append(txt)
                current_char_count += len(txt)
            current_speaker = spk

        if current_para:
            paragraphs.append(" ".join(current_para))

        res = "\n\n".join(paragraphs)
        res = re.sub(r' +', ' ', res)
        return re.sub(r'\s+([,\.!?:;।])', r'\1', res).strip()

    # If string is passed (e.g. from chapter textbox)
    lines = str(text_or_segments).splitlines()
    clean_items = []
    current_para = []
    current_char_count = 0

    for line in lines:
        cleaned = line.strip()
        if not cleaned:
            if current_para:
                clean_items.append(" ".join(current_para))
                current_para = []
                current_char_count = 0
            continue

        had_tag_boundary = bool(re.search(r'Chapter\s*\d+|\[(?:Speaker|\bEN\b|\bBN\b|\bHI\b)', line, re.IGNORECASE))

        # Strip timestamps: [00:00 --> 00:05], 00:00-00:30, [00:00:00 - 00:00:15], etc.
        cleaned = re.sub(r'\[?\b\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\s*(?:-->|-)\s*\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\]?', '', cleaned).strip()
        cleaned = re.sub(r'\[?\b\d{1,2}:\d{2}(?::\d{2})?\b\]?', '', cleaned).strip()

        # Strip speaker & language tags: [Speaker 1 | BN], [Speaker 2], [BN], [EN], etc.
        cleaned = re.sub(r'\[(?:Speaker\s*\d+|Auto|\w{2,10})(?:\s*\|\s*[\w\-]+)?\]', '', cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'\[[^\]]*?(?:Speaker|\bEN\b|\bBN\b|\bHI\b)[^\]]*?\]', '', cleaned, flags=re.IGNORECASE).strip()

        # Strip Chapter prefix: Chapter 1:, Chapter 02 -, etc.
        cleaned = re.sub(r'^Chapter\s*\d+\s*[:\-]\s*', '', cleaned, flags=re.IGNORECASE).strip()

        # Strip leading bullet points or numbers
        cleaned = re.sub(r'^[\-\*(?:\•)]\s*', '', cleaned).strip()

        if cleaned:
            if had_tag_boundary and current_para:
                clean_items.append(" ".join(current_para))
                current_para = []
                current_char_count = 0
            current_para.append(cleaned)
            current_char_count += len(cleaned)

    if current_para:
        clean_items.append(" ".join(current_para))

    res = "\n\n".join(clean_items)
    res = re.sub(r' +', ' ', res)
    return re.sub(r'\s+([,\.!?:;।])', r'\1', res).strip()

def export_transcript(segments, format_type="txt", file_path=None):
    """Export transcription to TXT, Clean TXT, JSON, SRT, VTT, or CSV with speaker & language tags."""
    if format_type in ("clean_txt", "clean"):
        content = clean_transcript_text(segments)
    elif format_type == "txt":
        lines = []
        for s in segments:
            spk = s.get("speaker", "Speaker 1")
            lng = s.get("language") or detect_segment_language(s.get("text", ""))
            lines.append(f"[{format_seconds(s['start'])} --> {format_seconds(s['end'])}] [{spk} | {lng}] {s['text'].strip()}")
        content = "\n".join(lines)
    elif format_type == "json":
        content = json.dumps(segments, indent=2, ensure_ascii=False)
    elif format_type == "srt":
        lines = []
        for i, s in enumerate(segments, 1):
            def srt_time(sec):
                hrs = int(sec // 3600)
                mins = int((sec % 3600) // 60)
                secs = int(sec % 60)
                millis = int((sec - int(sec)) * 1000)
                return f"{hrs:02}:{mins:02}:{secs:02},{millis:03}"
            spk = s.get("speaker", "Speaker 1")
            lng = s.get("language") or detect_segment_language(s.get("text", ""))
            lines.append(f"{i}\n{srt_time(s['start'])} --> {srt_time(s['end'])}\n[{spk} | {lng}] {s['text'].strip()}\n")
        content = "\n".join(lines)
    elif format_type == "vtt":
        lines = ["WEBVTT\n"]
        for i, s in enumerate(segments, 1):
            def vtt_time(sec):
                hrs = int(sec // 3600)
                mins = int((sec % 3600) // 60)
                secs = int(sec % 60)
                millis = int((sec - int(sec)) * 1000)
                return f"{hrs:02}:{mins:02}:{secs:02}.{millis:03}"
            spk = s.get("speaker", "Speaker 1")
            lng = s.get("language") or detect_segment_language(s.get("text", ""))
            lines.append(f"{i}\n{vtt_time(s['start'])} --> {vtt_time(s['end'])}\n<v {spk}>({lng}) {s['text'].strip()}\n")
        content = "\n".join(lines)
    elif format_type == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Index", "Start", "End", "Speaker", "Language", "Duration_Sec", "Text"])
        for i, s in enumerate(segments, 1):
            spk = s.get("speaker", "Speaker 1")
            lng = s.get("language") or detect_segment_language(s.get("text", ""))
            writer.writerow([i, format_seconds(s['start']), format_seconds(s['end']), spk, lng, round(s['end'] - s['start'], 2), s['text'].strip()])
        content = output.getvalue()
    else:
        content = "\n".join([s['text'].strip() for s in segments])

    if file_path:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return content
