"""
TinyLytic Background Workers
Multi-threaded QThread workers for transcription, YouTube downloading, live recording,
OpenCV slide/image processing, and AI chat generation.
"""

import os
import sys
import time
import tempfile
import glob
import warnings

# Suppress PyTorch CUDA toolkit / JIT warnings in terminal
os.environ["CUDA_MODULE_LOADING"] = "LAZY"
os.environ["TORCH_CPP_LOG_LEVEL"] = "ERROR"
warnings.filterwarnings("ignore", message=".*CUDA.*")
warnings.filterwarnings("ignore", category=UserWarning)
from PyQt6.QtCore import QThread, pyqtSignal
from core_engine import (
    get_temp_dir, setup_ffmpeg, resource_path,
    segments_to_chapters, format_seconds,
    perform_speaker_diarization, detect_segment_language,
    format_multilingual_punctuation
)

# Ensure FFmpeg is available
setup_ffmpeg()

# Safe imports
try:
    import whisper
    import torch
    HAS_WHISPER = True
except Exception:
    HAS_WHISPER = False
    whisper = None
    torch = None

try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    HAS_SOUND = True
    HAS_SD = True
except Exception:
    HAS_SOUND = False
    HAS_SD = False
    sd = None
    sf = None
    np = None

try:
    import yt_dlp
    HAS_YTDLP = True
except Exception:
    HAS_YTDLP = False
    yt_dlp = None


class UnifiedTranscriptionWorker(QThread):
    """Robust Whisper transcription worker with multi-language, translate, and multi-device support."""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    result = pyqtSignal(str, list)  # (formatted_text, segments_list)
    error = pyqtSignal(str)

    def __init__(self, media_path, model_id="tiny", language=None, task="transcribe", max_chunk_len=100, num_speakers=1, device="auto"):
        super().__init__()
        self.media_path = media_path
        self.model_id = model_id
        self.language = language
        self.task = task
        self.max_chunk_len = max_chunk_len
        self.num_speakers = num_speakers
        self.selected_device = device
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if not HAS_WHISPER:
            self.error.emit("OpenAI Whisper or PyTorch is not installed in the current environment.")
            return

        if not os.path.exists(self.media_path):
            self.error.emit(f"Audio/video file not found: {self.media_path}")
            return

        try:
            self.progress.emit(10)
            self.status.emit("Detecting hardware acceleration...")

            # Resolve compute device
            dev_req = str(self.selected_device).lower()
            if dev_req == "auto":
                actual_device = "cuda" if (torch and torch.cuda.is_available()) else "cpu"
            elif dev_req in ("hybrid", "both", "multi_gpu"):
                if torch and torch.cuda.is_available():
                    actual_device = "cuda:0"
                else:
                    actual_device = "cpu"
            elif dev_req.startswith("cuda"):
                if torch and torch.cuda.is_available():
                    actual_device = dev_req
                else:
                    actual_device = "cpu"
            elif dev_req == "cpu":
                actual_device = "cpu"
            else:
                actual_device = "cuda" if (torch and torch.cuda.is_available()) else "cpu"

            fp16 = True if actual_device.startswith("cuda") else False

            # Set thread allocation for CPU
            if actual_device == "cpu" or dev_req in ("hybrid", "both"):
                try:
                    import psutil
                    cores = psutil.cpu_count(logical=True) or 6
                    torch.set_num_threads(min(8, cores))
                except Exception:
                    pass

            self.progress.emit(20)
            dev_display = actual_device.upper()
            if dev_req in ("hybrid", "both"):
                dev_display = f"{actual_device.upper()} + CPU (Hybrid)"
            self.status.emit(f"Loading Whisper model ({self.model_id}) on {dev_display}...")

            # Check if model_id is a local file or standard name
            model_to_load = self.model_id
            models_dir = resource_path("models")

            # Map clean names like "Recommended" or "medium" to local whisper-medium.pt if present
            if str(self.model_id).lower() in ("recommended", "medium", "whisper-medium"):
                candidate_med = os.path.join(models_dir, "whisper-medium.pt")
                if os.path.exists(candidate_med):
                    model_to_load = candidate_med
                else:
                    model_to_load = "medium"
            elif str(self.model_id).lower() in ("tiny", "base", "small", "large-v3"):
                cand = os.path.join(models_dir, f"{str(self.model_id).lower()}.pt")
                if os.path.exists(cand):
                    model_to_load = cand
                else:
                    model_to_load = str(self.model_id).lower()
            elif not os.path.exists(model_to_load):
                # Check models folder for matching file
                candidate_pt = os.path.join(models_dir, f"{self.model_id}.pt")
                if os.path.exists(candidate_pt):
                    model_to_load = candidate_pt

            whisper_model = whisper.load_model(model_to_load, device=actual_device)

            if self._is_cancelled:
                return

            self.progress.emit(45)
            lang_label = self.language if self.language else "Auto Lang"
            self.status.emit(f"Transcribing audio ({lang_label}, task={self.task})...")

            # Load full audio array for analysis
            audio_arr = whisper.load_audio(self.media_path)
            duration_sec = len(audio_arr) / 16000.0

            # Base transcription arguments (optimized for speed & word timestamps)
            transcribe_args = {
                "task": self.task,
                "fp16": fp16,
                "verbose": False,
                "temperature": 0.0,
                "condition_on_previous_text": False,
                "word_timestamps": True
            }
            if not fp16:
                transcribe_args["beam_size"] = 1
                transcribe_args["best_of"] = 1

            # Check if dynamic multilingual / code-switching mode applies
            is_multilingual_mode = (self.language in (None, "multilang", "bilingual_bn_en", "auto"))

            if is_multilingual_mode and duration_sec > 35.0:
                # Dynamic Windowing for mixed languages (e.g. English intro transitioning into Bengali)
                self.status.emit("Analyzing audio with dynamic multilingual windowing...")
                total_samples = len(audio_arr)
                chunk_len_samples = 16000 * 30
                search_win = 16000 * 4
                curr_sample = 0
                chunks_list = []

                while curr_sample < total_samples:
                    target = curr_sample + chunk_len_samples
                    if target >= total_samples - (16000 * 10):
                        end_pt = total_samples
                    else:
                        start_search = max(curr_sample + 16000 * 20, target - search_win)
                        end_search = min(total_samples, target + search_win)
                        search_region = audio_arr[start_search:end_search]
                        frame_len = int(16000 * 0.1)
                        num_frames = len(search_region) // frame_len
                        if num_frames > 0:
                            energies = [float(np.mean(search_region[i*frame_len:(i+1)*frame_len]**2)) for i in range(num_frames)]
                            min_frame = int(np.argmin(energies))
                            end_pt = start_search + min_frame * frame_len
                        else:
                            end_pt = min(total_samples, target)
                    chunks_list.append((curr_sample, end_pt))
                    curr_sample = end_pt

                total_chunks = len(chunks_list)
                all_segments = []

                for idx, (c_start, c_end) in enumerate(chunks_list):
                    if self._is_cancelled:
                        return
                    c_audio = audio_arr[c_start:c_end]
                    c_offset_sec = float(c_start) / 16000.0

                    # Dynamic per-window language detection
                    mel_c = whisper.log_mel_spectrogram(whisper.pad_or_trim(c_audio)).to(whisper_model.device)
                    _, probs = whisper_model.detect_language(mel_c)
                    top_lang = max(probs, key=probs.get)
                    en_prob = probs.get('en', 0.0)
                    bn_prob = probs.get('bn', 0.0)
                    hi_prob = probs.get('hi', 0.0)

                    # Balanced multilingual & code-switching detection
                    bilingual_prompt = "Transcribe English and Bengali speech accurately. বাংলা হরফ এবং English words together with correct Bengali punctuation (দাঁড়ি ।) and English punctuation."
                    if bn_prob > 0.80 and bn_prob > en_prob * 2.0:
                        c_lang = 'bn'
                        c_prompt = "বাংলা হরফে স্পষ্ট প্রতিলিপি। সঠিক দাঁড়ি (।) এবং কমা (,) ব্যবহার করুন।"
                    elif en_prob > 0.80 and en_prob > bn_prob * 2.0:
                        c_lang = 'en'
                        c_prompt = None
                    elif hi_prob > 0.80 and hi_prob > en_prob * 2.0:
                        c_lang = 'hi'
                        c_prompt = "हिन्दी में स्पष्ट प्रतिलेखन।"
                    else:
                        # Mixed speech / code-switching: do not lock tokenizer
                        c_lang = None
                        c_prompt = bilingual_prompt

                    pct = 45 + int((idx / total_chunks) * 35)
                    self.progress.emit(pct)
                    disp_tag = c_lang.upper() if c_lang else "BILINGUAL"
                    self.status.emit(f"Transcribing segment {idx+1}/{total_chunks} [{disp_tag}]...")

                    c_args = dict(transcribe_args)
                    c_args["audio"] = c_audio
                    if c_lang:
                        c_args["language"] = c_lang
                    else:
                        c_args.pop("language", None)
                    if c_prompt:
                        c_args["initial_prompt"] = c_prompt

                    c_res = whisper_model.transcribe(**c_args)
                    for seg in c_res.get("segments", []):
                        seg["start"] = float(seg["start"]) + c_offset_sec
                        seg["end"] = float(seg["end"]) + c_offset_sec
                        for w in seg.get("words", []):
                            w["start"] = float(w["start"]) + c_offset_sec
                            w["end"] = float(w["end"]) + c_offset_sec
                        all_segments.append(seg)

                segments = all_segments
                full_text = " ".join(s.get("text", "").strip() for s in segments)
            else:
                # Single pass for short files or explicitly chosen languages
                transcribe_args["audio"] = audio_arr
                if self.language in ("bn", "bengali"):
                    transcribe_args["language"] = "bn"
                    transcribe_args["initial_prompt"] = "বাংলা হরফে স্পষ্ট প্রতিলিপি। সঠিক দাঁড়ি (।) এবং কমা (,) ব্যবহার করুন।"
                elif self.language in ("hi", "hindi"):
                    transcribe_args["language"] = "hi"
                    transcribe_args["initial_prompt"] = "हिन्दी में स्पष्ट प्रतिलेखन।"
                elif self.language and self.language not in ("multilang", "auto"):
                    transcribe_args["language"] = self.language
                else:
                    # Auto Lang on short audio: detect language directly across audio
                    mel = whisper.log_mel_spectrogram(whisper.pad_or_trim(audio_arr)).to(whisper_model.device)
                    _, probs = whisper_model.detect_language(mel)
                    top_lang = max(probs, key=probs.get)
                    en_prob = probs.get('en', 0.0)
                    bn_prob = probs.get('bn', 0.0)
                    hi_prob = probs.get('hi', 0.0)

                    # Balanced language detection on short / single-pass audio
                    bilingual_prompt = "Transcribe English and Bengali speech accurately. বাংলা হরফ এবং English words together with correct Bengali punctuation (দাঁড়ি ।) and English punctuation."
                    if bn_prob > 0.80 and bn_prob > en_prob * 2.0:
                        transcribe_args["language"] = "bn"
                        transcribe_args["initial_prompt"] = "বাংলা হরফে স্পষ্ট প্রতিলিপি। সঠিক দাঁড়ি (।) এবং কমা (,) ব্যবহার করুন।"
                    elif en_prob > 0.80 and en_prob > bn_prob * 2.0:
                        transcribe_args["language"] = "en"
                    elif hi_prob > 0.80 and hi_prob > en_prob * 2.0:
                        transcribe_args["language"] = "hi"
                        transcribe_args["initial_prompt"] = "हिन्दी में स्पष्ट प्रतिलेखन।"
                    else:
                        # Auto / mixed code-switching
                        transcribe_args.pop("language", None)
                        transcribe_args["initial_prompt"] = bilingual_prompt

                transcript = whisper_model.transcribe(**transcribe_args)
                segments = transcript.get("segments", [])
                full_text = transcript.get("text", "").strip()

            if self._is_cancelled:
                return

            # Apply punctuation helpers and language tags to every segment
            for seg in segments:
                raw = seg.get("text", "").strip()
                lng = seg.get("language") or detect_segment_language(raw)
                seg["language"] = lng
                seg["text"] = format_multilingual_punctuation(raw, lng)

            # Speaker Diarization
            should_diarize = (self.num_speakers in ("auto", "Auto") or (isinstance(self.num_speakers, int) and self.num_speakers > 1))
            if should_diarize:
                self.progress.emit(70)
                spk_label = "Auto Multi-Speaker" if self.num_speakers in ("auto", "Auto") else f"{self.num_speakers} speakers"
                self.status.emit(f"Performing acoustic voice separation ({spk_label})...")
                segments = perform_speaker_diarization(self.media_path, segments, num_speakers=self.num_speakers)

            self.progress.emit(88)
            self.status.emit("Generating formatted chapter timestamps with speaker & language tags...")

            formatted_text = segments_to_chapters(
                segments,
                max_chunk_len=self.max_chunk_len,
                include_speaker=should_diarize,
                include_lang=True
            )

            if not formatted_text.strip():
                # Fallback to plain text if no segments
                formatted_text = transcript.get("text", "").strip()

            self.progress.emit(100)
            self.status.emit("Transcription completed successfully!")
            self.result.emit(formatted_text, segments)

        except Exception as e:
            self.progress.emit(0)
            self.error.emit(f"Transcription error: {str(e)}")


# Backwards compatibility alias for older imports
TranscriptionWorker = UnifiedTranscriptionWorker


class YouTubeDownloadWorker(QThread):
    """Downloads YouTube audio using yt_dlp with embedded FFmpeg."""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    completed = pyqtSignal(str)  # returns downloaded audio path
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.downloaded_audio_path = None

    def run(self):
        if not HAS_YTDLP:
            self.error.emit("yt-dlp is not installed.")
            return

        try:
            self.progress.emit(10)
            self.status.emit("Connecting to YouTube...")

            out_dir = get_temp_dir()
            out_template = os.path.join(out_dir, f"yt_audio_{int(time.time())}.%(ext)s")

            ffmpeg_bin = setup_ffmpeg()
            ffmpeg_dir = os.path.dirname(os.path.abspath(ffmpeg_bin)) if (ffmpeg_bin and os.path.isfile(ffmpeg_bin)) else None

            base_opts = {
                "format": "bestaudio/best",
                "outtmpl": out_template,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
            }

            # Check if cookies.txt is provided by user in project or temp dir
            possible_cookies = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt"),
                os.path.join(get_temp_dir(), "cookies.txt"),
                os.path.expanduser("~/cookies.txt")
            ]
            for cp in possible_cookies:
                if os.path.isfile(cp) and os.path.getsize(cp) > 0:
                    base_opts["cookiefile"] = cp
                    break

            if ffmpeg_dir:
                base_opts["ffmpeg_location"] = ffmpeg_dir
                base_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]

            self.progress.emit(30)
            self.status.emit("Downloading audio stream...")

            title = "YouTube Audio"
            success = False
            last_err = None

            strategies = [
                ("Clean standard client", {}),
                ("iOS mobile client", {"extractor_args": {"youtube": {"player_client": ["ios"]}}}),
                ("Android client", {"extractor_args": {"youtube": {"player_client": ["android"]}}}),
                ("TV embedded client", {"extractor_args": {"youtube": {"player_client": ["tv_embedded"]}}}),
                ("Mobile web client", {"extractor_args": {"youtube": {"player_client": ["mweb"]}}})
            ]

            for strat_name, extra_opts in strategies:
                curr_opts = dict(base_opts)
                curr_opts.update(extra_opts)
                try:
                    self.status.emit(f"Connecting ({strat_name})...")
                    with yt_dlp.YoutubeDL(curr_opts) as ydl:
                        info = ydl.extract_info(self.url, download=True)
                        title = info.get("title", "YouTube Audio")
                        success = True
                        break
                except Exception as dl_err:
                    last_err = dl_err
                    err_str = str(dl_err).lower()
                    if "postprocessing" in err_str or "ffprobe" in err_str or "ffmpeg" in err_str:
                        base_opts.pop("postprocessors", None)
                    continue

            if not success:
                raise last_err or RuntimeError("Could not download YouTube stream.")

            self.progress.emit(90)
            self.status.emit("Locating downloaded file...")

            # Locate latest audio file
            candidate_files = sorted(
                glob.glob(os.path.join(out_dir, "yt_audio_*.*")),
                key=os.path.getmtime,
                reverse=True
            )

            if candidate_files:
                self.downloaded_audio_path = candidate_files[0]
                self.progress.emit(100)
                clean_title = "".join(c for c in str(title) if c.isprintable() and ord(c) < 128).strip() or "Audio"
                self.status.emit(f"Downloaded: {clean_title[:50]}")
                self.completed.emit(self.downloaded_audio_path)
            else:
                self.error.emit("Could not locate extracted audio file.")

        except Exception as e:
            self.error.emit(f"YouTube download failed: {str(e)}")


class RealtimeRecorderWorker(QThread):
    """High-reliability sounddevice recording worker with real-time volume calculation."""
    volume_level = pyqtSignal(float)
    recording_time = pyqtSignal(str)
    status = pyqtSignal(str)
    finished_recording = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, output_path=None, device_index=None, samplerate=16000):
        super().__init__()
        self.output_path = output_path or os.path.join(get_temp_dir(), f"live_record_{int(time.time())}.wav")
        self.device_index = device_index
        self.samplerate = samplerate
        self.is_recording = False
        self.start_time = None

    def stop(self):
        self.is_recording = False

    def run(self):
        if not HAS_SOUND:
            self.error.emit("sounddevice or soundfile library is not installed.")
            return

        self.is_recording = True
        self.start_time = time.time()
        self.status.emit("Recording...")

        try:
            native_sr = 44100
            native_channels = 1
            if HAS_SD:
                try:
                    if self.device_index is not None:
                        dev_info = sd.query_devices(self.device_index)
                    else:
                        dev_info = sd.query_devices(kind='input')
                    if dev_info:
                        native_channels = min(2, max(1, dev_info.get('max_input_channels', 1)))
                        native_sr = int(dev_info.get('default_samplerate', 44100))
                except Exception:
                    native_channels = 1
                    native_sr = 44100

            recorded_chunks = []

            def audio_callback(indata, frames, time_info, status_flags):
                if not self.is_recording:
                    raise sd.CallbackStop()
                # Downmix multi-channel to mono
                if indata.ndim > 1 and indata.shape[1] > 1:
                    mono = np.mean(indata, axis=1)
                else:
                    mono = indata.flatten()
                recorded_chunks.append(mono.copy())
                peak = float(np.max(np.abs(mono))) if len(mono) > 0 else 0.0
                self.volume_level.emit(min(peak * 1.5, 1.0))

            # Resilient multi-tier stream opening: chosen device -> default input -> 16kHz mono safe fallback
            stream = None
            try:
                stream_args = {
                    "samplerate": native_sr,
                    "channels": native_channels,
                    "callback": audio_callback,
                    "blocksize": int(native_sr * 0.1)
                }
                if self.device_index is not None:
                    stream_args["device"] = self.device_index
                stream = sd.InputStream(**stream_args)
            except Exception as e1:
                print(f"[RealtimeRecorderWorker] Stream open failed on device {self.device_index}: {e1}. Retrying with safe default input...")
                try:
                    stream = sd.InputStream(channels=min(2, native_channels), samplerate=44100, callback=audio_callback, blocksize=int(44100 * 0.1))
                except Exception as e2:
                    print(f"[RealtimeRecorderWorker] Default input fallback failed: {e2}. Falling back to 16kHz mono...")
                    stream = sd.InputStream(channels=1, samplerate=16000, callback=audio_callback, blocksize=1600)

            with stream:
                while self.is_recording:
                    elapsed = int(time.time() - self.start_time)
                    hrs = elapsed // 3600
                    mins = (elapsed % 3600) // 60
                    secs = elapsed % 60
                    self.recording_time.emit(f"{hrs:02}:{mins:02}:{secs:02}")
                    sd.sleep(100)

            # Assemble full audio and apply vocal enhancement
            if recorded_chunks:
                full_audio = np.concatenate(recorded_chunks)
            else:
                full_audio = np.array([], dtype=np.float32)

            if len(full_audio) > 0:
                full_audio = full_audio - float(np.mean(full_audio))
                peak = float(np.max(np.abs(full_audio)))
                if peak > 0.005:
                    full_audio = (full_audio / peak) * 0.95

                # Resample to 16 kHz if necessary
                if native_sr != 16000 and len(full_audio) > 0:
                    try:
                        import scipy.signal
                        target_samples = int(len(full_audio) * 16000 / native_sr)
                        full_audio = scipy.signal.resample(full_audio, target_samples)
                        target_sr = 16000
                    except Exception:
                        target_sr = native_sr
                else:
                    target_sr = native_sr

                sf.write(self.output_path, full_audio, target_sr, subtype='PCM_16')
            else:
                sf.write(self.output_path, np.zeros(16000, dtype=np.float32), 16000, subtype='PCM_16')

            self.status.emit("Recording saved.")
            self.finished_recording.emit(self.output_path)

        except Exception as e:
            self.error.emit(f"Audio recording error: {str(e)}")


class VisionAnalysisWorker(QThread):
    """Background worker for video slide detection or image OCR."""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    result = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, mode="video_slides", file_path="", interval_sec=4):
        super().__init__()
        self.mode = mode
        self.file_path = file_path
        self.interval_sec = interval_sec

    def run(self):
        try:
            from vision_engine import perform_image_ocr, analyze_video_slides

            if self.mode == "image_ocr":
                self.status.emit("Analyzing image with OpenCV and OCR...")
                self.progress.emit(30)
                res = perform_image_ocr(self.file_path)
                self.progress.emit(100)
                self.result.emit(res)

            elif self.mode == "video_slides":
                self.status.emit("Scanning video for slide changes and on-screen text...")

                def on_progress(p):
                    self.progress.emit(p)
                    self.status.emit(f"Analyzing video frames... {p}%")

                res = analyze_video_slides(self.file_path, progress_callback=on_progress, interval_seconds=self.interval_sec)
                self.status.emit(f"Completed! Detected {res['total_slides']} visual slide transitions.")
                self.result.emit(res)

        except Exception as e:
            self.error.emit(f"Vision processing failed: {str(e)}")


class ChatWorker(QThread):
    """Background worker for AI Chat responses."""
    response_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, chat_manager, query, model_choice):
        super().__init__()
        self.chat_manager = chat_manager
        self.query = query
        self.model_choice = model_choice

    def run(self):
        try:
            reply = self.chat_manager.generate_response(self.query, self.model_choice)
            self.response_ready.emit(reply)
        except Exception as e:
            self.error.emit(f"Chat generation error: {str(e)}")


class ModelDownloadWorker(QThread):
    """Background worker to download official Whisper models into models directory with live progress."""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str, bool, str)  # (model_key, success, message)

    def __init__(self, model_key, url, target_path):
        super().__init__()
        self.model_key = model_key
        self.url = url
        self.target_path = target_path
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        import urllib.request
        temp_path = self.target_path + ".part"
        try:
            self.status.emit(f"Connecting to official repository for {self.model_key}...")
            self.progress.emit(2)

            os.makedirs(os.path.dirname(self.target_path), exist_ok=True)

            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "TinyLytic-ModelDownloader/2.0"}
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                chunk_size = 1024 * 512  # 512 KB chunks

                with open(temp_path, "wb") as f:
                    while True:
                        if self._is_cancelled:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                            self.finished.emit(self.model_key, False, "Download cancelled.")
                            return

                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int((downloaded / total_size) * 100)
                            self.progress.emit(pct)
                            mb_down = downloaded / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            self.status.emit(f"Downloading {self.model_key}... {mb_down:.1f} MB / {mb_total:.1f} MB ({pct}%)")

            if os.path.exists(self.target_path):
                os.remove(self.target_path)
            os.rename(temp_path, self.target_path)

            self.progress.emit(100)
            self.finished.emit(self.model_key, True, f"Model {self.model_key} downloaded successfully.")

        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            self.finished.emit(self.model_key, False, f"Download failed: {str(e)}")


class CudaInstallWorker(QThread):
    """Background worker to install PyTorch CUDA support via pip in the background."""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def run(self):
        import subprocess, sys
        try:
            self.status.emit("Initiating PyTorch CUDA installation via pip...")
            self.progress.emit(10)

            cmd = [
                sys.executable, "-m", "pip", "install",
                "torch", "torchvision", "torchaudio",
                "--index-url", "https://download.pytorch.org/whl/cu124",
                "--upgrade"
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            pct = 15
            for line in process.stdout:
                line_str = line.strip()
                if "Downloading" in line_str:
                    pct = min(85, pct + 2)
                    self.progress.emit(pct)
                    self.status.emit(f"Downloading CUDA packages: {line_str[:60]}...")
                elif "Installing" in line_str:
                    self.progress.emit(90)
                    self.status.emit("Installing CUDA wheels...")

            process.wait()

            if process.returncode == 0:
                self.progress.emit(100)
                self.finished.emit(True, "PyTorch CUDA installed successfully! Restart or refresh to activate RTX 3060 acceleration.")
            else:
                self.finished.emit(False, f"Installation finished with code {process.returncode}.")

        except Exception as e:
            self.finished.emit(False, f"Installation error: {str(e)}")


class PackageUpdateWorker(QThread):
    """Background thread to check and update yt-dlp and core packages."""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, packages=None):
        super().__init__()
        self.packages = packages or ["yt-dlp", "openai-whisper"]

    def run(self):
        try:
            total = len(self.packages)
            for idx, pkg in enumerate(self.packages):
                pct = int((idx / total) * 100)
                self.progress.emit(pct)
                self.status.emit(f"Updating {pkg} to latest release...")

                cmd = [sys.executable, "-m", "pip", "install", "--upgrade", pkg]
                startupinfo = None
                if sys.platform == "win32":
                    import subprocess
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = 0  # SW_HIDE

                import subprocess
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=startupinfo)
                if res.returncode != 0:
                    self.status.emit(f"Note: {pkg} returned code {res.returncode}")

            self.progress.emit(100)
            self.status.emit("Package update check completed successfully!")
            self.finished.emit(True, "Packages updated to the latest versions.")
        except Exception as e:
            self.progress.emit(0)
            self.status.emit(f"Update failed: {str(e)}")
            self.finished.emit(False, str(e))
