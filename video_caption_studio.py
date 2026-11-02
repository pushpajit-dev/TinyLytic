"""
TinyLytic Video Caption Studio
Interactive Video Preview, Beat-by-Beat Word Synchronization,
Comprehensive Typography Editing, and Multi-Format Video Export (MP4, Green Screen, Transparent).
"""

import os
import sys
import time
import math
import zipfile
import subprocess
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    cv2 = None

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QSpinBox, QColorDialog, QCheckBox, QGroupBox,
    QFileDialog, QMessageBox, QProgressBar, QSplitter, QScrollArea,
    QFormLayout, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QImage, QPixmap, QColor, QFont, QIcon
from core_engine import format_seconds, setup_ffmpeg, resource_path


class CaptionStyle:
    """Settings data structure for Caption Typography and Layout."""
    def __init__(self):
        self.font_family = "Segoe UI"
        self.font_size = 38
        self.is_bold = True
        self.is_italic = False
        self.text_color = (255, 255, 255)         # RGB
        self.highlight_color = (255, 220, 0)      # RGB (Active Spoken Word)
        self.bg_box_enabled = True
        self.bg_color = (15, 15, 15)              # RGB
        self.bg_opacity = 0.65                    # 0.0 - 1.0
        self.bg_padding = 12
        self.stroke_width = 3
        self.stroke_color = (0, 0, 0)             # RGB
        self.shadow_offset = 4
        self.shadow_color = (20, 20, 20)          # RGB
        self.position = "Bottom"                  # Bottom, Center, Top, Custom
        self.vertical_offset_pct = 82             # 0 to 100%
        self.alignment = "Center"                 # Left, Center, Right
        self.animation = "None"                   # None, Pop, Fade, Slide, Jump, Color Outline, Smooth Blur
        self.anim_scope_all = True                # True = All Captions, False = Only Start and End Captions
        self.line_gap = 8                         # Line Gap / Paragraph Spacing in pixels (0 to 40)


def get_system_font(font_family="Segoe UI", font_size=38, is_bold=False):
    """Find and load TTF font with fallback to Nirmala UI or Segoe UI for Bengali Unicode script."""
    candidates = []
    win_fonts = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")

    if is_bold:
        family_map = {
            "Segoe UI": ["segoeuib.ttf", "segoeui.ttf"],
            "Nirmala UI": ["NirmalaB.ttf", "Nirmala.ttf"],
            "Arial": ["arialbd.ttf", "arial.ttf"],
            "Impact": ["impact.ttf"],
            "Trebuchet MS": ["trebucbd.ttf", "trebuc.ttf"],
            "Verdana": ["verdanab.ttf", "verdana.ttf"],
            "Montserrat": ["Montserrat-Bold.ttf", "arialbd.ttf"]
        }
    else:
        family_map = {
            "Segoe UI": ["segoeui.ttf"],
            "Nirmala UI": ["Nirmala.ttf"],
            "Arial": ["arial.ttf"],
            "Impact": ["impact.ttf"],
            "Trebuchet MS": ["trebuc.ttf"],
            "Verdana": ["verdana.ttf"],
            "Montserrat": ["Montserrat-Regular.ttf", "arial.ttf"]
        }

    filenames = family_map.get(font_family, ["segoeui.ttf", "Nirmala.ttf", "arial.ttf"])
    for fn in filenames:
        candidates.append(os.path.join(win_fonts, fn))

    # Universal fallbacks (Nirmala UI has native Bengali + Devanagari support)
    candidates.append(os.path.join(win_fonts, "Nirmala.ttf"))
    candidates.append(os.path.join(win_fonts, "segoeui.ttf"))
    candidates.append(os.path.join(win_fonts, "arial.ttf"))

    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, font_size)
            except Exception:
                continue

    return ImageFont.load_default()


def render_caption_frame(base_bgr_frame, current_sec, segments, style: CaptionStyle, mode="normal"):
    """
    Render beat-by-beat synchronized typography with motion animations onto a video frame.
    mode: 'normal' (overlay on video), 'green_screen' (solid #00FF00), 'transparent' (RGBA)
    """
    h, w = base_bgr_frame.shape[:2]
    scale_factor = h / 1080.0

    # Find active segment for this timestamp
    active_seg = None
    active_seg_idx = -1
    for idx, seg in enumerate(segments):
        if seg.get("start", 0) <= current_sec <= seg.get("end", 0) + 0.3:
            active_seg = seg
            active_seg_idx = idx
            break

    # Background frame preparation
    if mode == "green_screen":
        pil_img = Image.new("RGBA", (w, h), (0, 255, 0, 255))
    elif mode == "transparent":
        pil_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    else:
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(base_bgr_frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame).convert("RGBA")

    if not active_seg:
        # No speech at this timestamp
        if mode == "transparent":
            return np.array(pil_img)
        return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)

    words = active_seg.get("words", [])
    raw_text = active_seg.get("text", "").strip()

    # If no word-level timestamps exist, split evenly
    if not words and raw_text:
        tokens = raw_text.split()
        seg_start = active_seg.get("start", 0)
        seg_dur = max(0.2, active_seg.get("end", 0) - seg_start)
        word_dur = seg_dur / max(1, len(tokens))
        words = []
        for i, tok in enumerate(tokens):
            w_s = seg_start + i * word_dur
            w_e = w_s + word_dur
            words.append({"word": tok, "start": w_s, "end": w_e})

    if not words:
        if mode == "transparent":
            return np.array(pil_img)
        return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)

    # -------------------------------------------------------------------------
    # Animation Parameters Calculation
    # -------------------------------------------------------------------------
    is_start_or_end = (active_seg_idx == 0 or active_seg_idx == len(segments) - 1)
    apply_anim = (style.animation != "None") and (style.anim_scope_all or is_start_or_end)

    pop_scale = 1.0
    alpha_mult = 1.0
    slide_offset_y = 0
    jump_offset_y = 0
    blur_radius = 0.0
    dynamic_stroke_color = style.stroke_color
    dynamic_stroke_w = style.stroke_width

    if apply_anim and active_seg:
        seg_start = active_seg.get("start", 0.0)
        seg_end = active_seg.get("end", seg_start + 1.0)
        dur = max(0.3, seg_end - seg_start)

        in_dur = min(0.35, dur * 0.35)
        out_dur = min(0.30, dur * 0.30)

        t_in = max(0.0, current_sec - seg_start)
        t_out = max(0.0, seg_end - current_sec)

        prog_in = min(1.0, t_in / in_dur) if in_dur > 0 else 1.0
        prog_out = min(1.0, t_out / out_dur) if out_dur > 0 else 1.0
        anim_factor = min(prog_in, prog_out)

        anim_type = style.animation

        if anim_type == "Pop":
            if prog_in < 1.0:
                if prog_in < 0.65:
                    pop_scale = 0.70 + (0.45 * (prog_in / 0.65))
                else:
                    pop_scale = 1.15 - (0.15 * ((prog_in - 0.65) / 0.35))
            elif prog_out < 1.0:
                pop_scale = max(0.75, prog_out)

        elif anim_type == "Fade":
            alpha_mult = max(0.0, min(1.0, anim_factor))

        elif anim_type == "Slide":
            if prog_in < 1.0:
                slide_offset_y = int(45.0 * (1.0 - prog_in) * scale_factor)
            elif prog_out < 1.0:
                slide_offset_y = int(35.0 * (1.0 - prog_out) * scale_factor)
            alpha_mult = max(0.0, min(1.0, anim_factor * 1.3))

        elif anim_type == "Jump":
            if prog_in < 1.0:
                jump_offset_y = -int(34.0 * math.sin(prog_in * math.pi) * scale_factor)

        elif anim_type == "Color Outline":
            phase = (current_sec * 5.0) % (2.0 * math.pi)
            pulse = (math.sin(phase) + 1.0) / 2.0
            r_glow = int(100 + 155 * pulse)
            g_glow = int(220 * (1.0 - pulse))
            b_glow = int(255 * pulse)
            dynamic_stroke_color = (r_glow, g_glow, b_glow)
            dynamic_stroke_w = max(1, int(style.stroke_width + 2.5 * pulse))

        elif anim_type == "Smooth Blur":
            blur_factor = 1.0 - anim_factor
            blur_radius = blur_factor * 7.5 * scale_factor
            alpha_mult = min(1.0, max(0.12, anim_factor))

    # Scale font size proportionally to video height (relative to 1080p)
    actual_font_size = max(14, int(style.font_size * scale_factor * pop_scale))
    font = get_system_font(style.font_family, actual_font_size, style.is_bold)

    # Calculate word bounding boxes
    draw = ImageDraw.Draw(pil_img)
    word_boxes = []
    total_text_w = 0
    space_w = draw.textlength(" ", font=font)
    max_h = actual_font_size * 1.3

    for item in words:
        tok = item.get("word", "").strip()
        if not tok:
            continue
        tw = draw.textlength(tok, font=font)
        word_boxes.append({
            "word": tok,
            "width": tw,
            "start": item.get("start", 0),
            "end": item.get("end", 0)
        })
        total_text_w += tw + space_w

    if not word_boxes:
        if mode == "transparent":
            return np.array(pil_img)
        return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)

    total_text_w -= space_w  # remove trailing space

    # Wrap words into lines if exceeding 85% of video width
    max_line_w = int(w * 0.86)
    lines = []
    curr_line = []
    curr_w = 0

    for wb in word_boxes:
        if curr_w + wb["width"] > max_line_w and curr_line:
            lines.append((curr_line, curr_w - space_w))
            curr_line = [wb]
            curr_w = wb["width"] + space_w
        else:
            curr_line.append(wb)
            curr_w += wb["width"] + space_w

    if curr_line:
        lines.append((curr_line, curr_w - space_w))

    # Calculate overall caption block height with user-controlled line gap
    line_spacing = int(actual_font_size * 0.22) + int(getattr(style, "line_gap", 8) * scale_factor)
    block_h = len(lines) * int(max_h) + (len(lines) - 1) * line_spacing

    # Vertical positioning with animation offsets
    if style.position == "Top":
        block_y = int(h * 0.08)
    elif style.position == "Center":
        block_y = int((h - block_h) / 2)
    elif style.position == "Custom":
        block_y = int(h * (style.vertical_offset_pct / 100.0) - (block_h / 2))
    else:  # Bottom (default)
        block_y = int(h * (style.vertical_offset_pct / 100.0) - block_h)

    block_y += slide_offset_y + jump_offset_y
    block_y = max(10, min(h - block_h - 10, block_y))

    # Draw on separate overlay for opacity blending
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    curr_y = block_y
    for line_words, line_w in lines:
        if style.alignment == "Left":
            curr_x = int(w * 0.08)
        elif style.alignment == "Right":
            curr_x = int(w * 0.92 - line_w)
        else:  # Center
            curr_x = int((w - line_w) / 2)

        # Draw translucent background box if enabled
        if style.bg_box_enabled and style.bg_opacity > 0:
            pad = int(style.bg_padding * scale_factor * pop_scale)
            box_rect = [
                curr_x - pad,
                curr_y - int(pad * 0.4),
                curr_x + line_w + pad,
                curr_y + int(max_h) + int(pad * 0.4)
            ]
            alpha = max(0, min(255, int(255 * style.bg_opacity * alpha_mult)))
            box_rgba = (*style.bg_color, alpha)
            overlay_draw.rounded_rectangle(box_rect, radius=int(8 * scale_factor), fill=box_rgba)

        # Draw words with beat-by-beat highlighting
        for wb in line_words:
            word_str = wb["word"]
            w_w = wb["width"]
            is_active_word = (wb["start"] <= current_sec <= wb["end"] + 0.15)

            fill_color = style.highlight_color if is_active_word else style.text_color
            fill_rgba = (*fill_color, max(0, min(255, int(255 * alpha_mult))))
            stroke_rgba = (*dynamic_stroke_color, max(0, min(255, int(255 * alpha_mult))))
            stroke_w = int(dynamic_stroke_w * scale_factor)

            # Drop Shadow
            if style.shadow_offset > 0:
                s_off = int(style.shadow_offset * scale_factor)
                shadow_rgba = (*style.shadow_color, max(0, min(255, int(180 * alpha_mult))))
                overlay_draw.text(
                    (curr_x + s_off, curr_y + s_off),
                    word_str,
                    font=font,
                    fill=shadow_rgba
                )

            # Stroke / Outline & Main Text
            overlay_draw.text(
                (curr_x, curr_y),
                word_str,
                font=font,
                fill=fill_rgba,
                stroke_width=stroke_w,
                stroke_fill=stroke_rgba if stroke_w > 0 else None
            )

            curr_x += w_w + space_w

        curr_y += int(max_h) + line_spacing

    # Apply smooth blur if configured
    if blur_radius > 0.6:
        try:
            overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        except Exception:
            pass

    # Composite overlay onto pil_img
    pil_img = Image.alpha_composite(pil_img, overlay)

    if mode == "transparent":
        return np.array(pil_img)
    return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)


class VideoExportWorker(QThread):
    """Background worker for exporting burned-in MP4, Green Screen MP4, or Transparent frames."""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, video_path, segments, style: CaptionStyle, export_mode="mp4", quality="High", output_path=""):
        super().__init__()
        self.video_path = video_path
        self.segments = segments
        self.style = style
        self.export_mode = export_mode  # 'mp4', 'green_screen', 'transparent_zip', 'transparent_mov'
        self.quality = quality          # 'High', 'Balanced', 'Fast'
        self.output_path = output_path
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if not HAS_CV2:
            self.finished.emit(False, "OpenCV is not available.")
            return

        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.finished.emit(False, f"Cannot open video: {self.video_path}")
                return

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            self.status.emit(f"Preparing {self.export_mode.upper()} export ({width}x{height} @ {fps:.2f} FPS)...")
            self.progress.emit(5)

            ffmpeg_bin = setup_ffmpeg() or "ffmpeg"

            # 1. TRANSPARENT PNG ZIP EXPORT
            if self.export_mode == "transparent_zip":
                temp_zip_dir = os.path.dirname(self.output_path)
                with zipfile.ZipFile(self.output_path, "w", zipfile.ZIP_DEFLATED) as zip_f:
                    frame_idx = 0
                    while True:
                        if self._is_cancelled:
                            cap.release()
                            self.finished.emit(False, "Export cancelled.")
                            return
                        ret, frame = cap.read()
                        if not ret:
                            break

                        current_sec = frame_idx / fps
                        rgba_frame = render_caption_frame(frame, current_sec, self.segments, self.style, mode="transparent")
                        # Save frame in memory as PNG
                        is_success, buffer = cv2.imencode(".png", cv2.cvtColor(rgba_frame, cv2.COLOR_RGBA2BGRA))
                        if is_success:
                            zip_f.writestr(f"caption_frame_{frame_idx:06d}.png", buffer.tobytes())

                        frame_idx += 1
                        if total_frames > 0 and frame_idx % 15 == 0:
                            pct = 5 + int((frame_idx / total_frames) * 90)
                            self.progress.emit(pct)
                            self.status.emit(f"Exporting transparent frames: {frame_idx}/{total_frames} ({pct}%)...")

                cap.release()
                self.progress.emit(100)
                self.finished.emit(True, f"Transparent frames ZIP successfully exported to:\n{self.output_path}")
                return

            # 2. VIDEO EXPORTS (MP4, Green Screen MP4, Transparent MOV)
            crf_val = "18" if self.quality == "High" else ("23" if self.quality == "Balanced" else "28")
            temp_raw_video = os.path.join(os.path.dirname(self.output_path), f"temp_render_{int(time.time())}.mp4")

            # Setup OpenCV VideoWriter or FFmpeg pipe
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(temp_raw_video, fourcc, fps, (width, height))

            render_mode = "green_screen" if self.export_mode == "green_screen" else "normal"
            frame_idx = 0

            while True:
                if self._is_cancelled:
                    cap.release()
                    writer.release()
                    if os.path.exists(temp_raw_video):
                        os.remove(temp_raw_video)
                    self.finished.emit(False, "Export cancelled.")
                    return

                ret, frame = cap.read()
                if not ret:
                    break

                current_sec = frame_idx / fps
                rendered_bgr = render_caption_frame(frame, current_sec, self.segments, self.style, mode=render_mode)
                writer.write(rendered_bgr)

                frame_idx += 1
                if total_frames > 0 and frame_idx % 20 == 0:
                    pct = 5 + int((frame_idx / total_frames) * 75)
                    self.progress.emit(pct)
                    self.status.emit(f"Rendering frame {frame_idx}/{total_frames} ({pct}%)...")

            cap.release()
            writer.release()

            self.progress.emit(85)
            self.status.emit("Muxing audio track and encoding high-quality video...")

            # Merge original audio using FFmpeg
            if os.path.exists(self.output_path):
                try:
                    os.remove(self.output_path)
                except Exception:
                    pass

            mux_cmd = [
                ffmpeg_bin, "-y",
                "-i", temp_raw_video,
                "-i", self.video_path,
                "-map", "0:v:0",
                "-map", "1:a:0?",
                "-c:v", "libx264",
                "-crf", crf_val,
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                self.output_path
            ]

            process = subprocess.run(mux_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)

            if os.path.exists(temp_raw_video):
                try:
                    os.remove(temp_raw_video)
                except Exception:
                    pass

            if process.returncode == 0 and os.path.exists(self.output_path):
                self.progress.emit(100)
                self.finished.emit(True, f"Video exported successfully!\nSaved to: {self.output_path}")
            else:
                # If audio muxing had an issue, fallback to renamed raw video
                if os.path.exists(temp_raw_video):
                    os.rename(temp_raw_video, self.output_path)
                    self.progress.emit(100)
                    self.finished.emit(True, f"Video exported (direct video stream):\nSaved to: {self.output_path}")
                else:
                    self.finished.emit(False, f"Encoding error: {process.stderr.decode('utf-8', errors='ignore')[:200]}")

        except Exception as e:
            self.finished.emit(False, f"Export error: {str(e)}")


class VideoCaptionStudioDialog(QDialog):
    """
    Dedicated Video Caption & Typography Studio.
    Provides live preview, beat-by-beat word highlighting, full typography styling,
    and MP4 / Green Screen / Transparent frame export.
    """

    def __init__(self, parent, video_path, segments):
        super().__init__(parent)
        self.setWindowTitle("TinyLytic - Video Caption Studio")
        self.resize(1180, 780)
        self.setMinimumSize(960, 640)
        self.video_path = video_path
        self.segments = segments or []
        self.style = CaptionStyle()

        # Window icon
        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Video playback state
        self.cap = None
        self.total_frames = 0
        self.fps = 30.0
        self.duration_sec = 0.0
        self.current_frame = 0
        self.is_playing = False
        self.export_worker = None

        self.initVideo()
        self.initAudio()
        self.initUI()

        # Playback timer
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self.advanceFrame)

        # Show initial frame
        self.showCurrentFrame()

    def initAudio(self):
        """Initialize synchronized audio playback engine via QtMultimedia."""
        self.audio_player = None
        self.audio_output = None
        try:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            from PyQt6.QtCore import QUrl
            self.audio_player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.audio_player.setAudioOutput(self.audio_output)
            self.audio_output.setVolume(1.0)

            if os.path.exists(self.video_path):
                abs_path = os.path.abspath(self.video_path)
                self.audio_player.setSource(QUrl.fromLocalFile(abs_path))

                # Handle audio decode errors with automatic PCM WAV extraction
                def on_media_error(error, error_string):
                    print(f"[Caption Studio Audio]: {error} - {error_string}. Extracting WAV track fallback...")
                    self.extractAndLoadFallbackAudio()
                self.audio_player.errorOccurred.connect(on_media_error)
        except Exception as e:
            print(f"[Caption Studio Audio Init Error]: {e}")

    def extractAndLoadFallbackAudio(self):
        """Extract audio stream to a PCM 16-bit WAV file asynchronously with timeout."""
        if getattr(self, '_fallback_audio_attempted', False):
            return
        self._fallback_audio_attempted = True
        import threading
        def worker():
            try:
                import tempfile, subprocess
                from PyQt6.QtCore import QUrl
                from core_engine import setup_ffmpeg
                ffmpeg_bin = setup_ffmpeg() or "ffmpeg"
                base_name = os.path.basename(self.video_path)
                safe_name = "".join(c for c in base_name if c.isalnum())[:20]
                wav_path = os.path.join(tempfile.gettempdir(), f"cs_{safe_name}.wav")
                if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 1000:
                    subprocess.run(
                        [ffmpeg_bin, "-y", "-i", self.video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", wav_path],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25
                    )
                if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000 and hasattr(self, 'audio_player') and self.audio_player:
                    self.audio_player.setSource(QUrl.fromLocalFile(wav_path))
            except Exception as e:
                print(f"[Caption Studio Audio Fallback Error]: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def onVolumeChanged(self, val):
        """Adjust playback volume."""
        if hasattr(self, 'audio_output') and self.audio_output:
            self.audio_output.setVolume(val / 100.0)

    def initVideo(self):
        if not HAS_CV2 or not os.path.exists(self.video_path):
            return
        self.cap = cv2.VideoCapture(self.video_path)
        if self.cap.isOpened():
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.duration_sec = self.total_frames / self.fps if self.fps > 0 else 0.0

    def initUI(self):
        main_layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #2d3748; }")

        # =====================================================================
        # LEFT: Video Preview & Playback Controls
        # =====================================================================
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)

        self.video_display = QLabel()
        self.video_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_display.setStyleSheet("background-color: #0d1117; border: 1px solid #2d3748; border-radius: 6px;")
        self.video_display.setMinimumSize(600, 380)
        preview_layout.addWidget(self.video_display, 1)

        # Scrubber / Timeline Slider
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, max(1, self.total_frames))
        self.seek_slider.sliderMoved.connect(self.onSeekMoved)
        self.seek_slider.sliderReleased.connect(self.onSeekReleased)
        preview_layout.addWidget(self.seek_slider)

        # Playback Control Row
        control_row = QHBoxLayout()

        self.btn_play = QPushButton("Play")
        self.btn_play.setStyleSheet("background-color: #2b6cb0; color: #ffffff; font-weight: bold; padding: 6px 14px;")
        self.btn_play.clicked.connect(self.togglePlay)
        control_row.addWidget(self.btn_play)

        btn_prev = QPushButton("< 1s")
        btn_prev.clicked.connect(lambda: self.seekRelative(-1.0))
        control_row.addWidget(btn_prev)

        btn_next = QPushButton("+ 1s >")
        btn_next.clicked.connect(lambda: self.seekRelative(1.0))
        control_row.addWidget(btn_next)

        self.time_label = QLabel(f"00:00 / {format_seconds(self.duration_sec)}")
        self.time_label.setStyleSheet("color: #e2e8f0; font-family: monospace; font-size: 11pt; padding: 0 8px;")
        control_row.addWidget(self.time_label)

        # Volume Slider for Audio Playback
        lbl_vol = QLabel("Vol:")
        lbl_vol.setStyleSheet("color: #a0aec0; padding-left: 6px;")
        control_row.addWidget(lbl_vol)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(100)
        self.vol_slider.setFixedWidth(75)
        self.vol_slider.setToolTip("Video Audio Volume")
        self.vol_slider.valueChanged.connect(self.onVolumeChanged)
        control_row.addWidget(self.vol_slider)

        control_row.addStretch()

        # Preset Buttons
        lbl_preset = QLabel("Presets:")
        lbl_preset.setStyleSheet("color: #a0aec0; font-weight: bold;")
        control_row.addWidget(lbl_preset)

        btn_pre_tiktok = QPushButton("TikTok Punch")
        btn_pre_tiktok.clicked.connect(lambda: self.applyPreset("tiktok"))
        control_row.addWidget(btn_pre_tiktok)

        btn_pre_box = QPushButton("Clean Box")
        btn_pre_box.clicked.connect(lambda: self.applyPreset("box"))
        control_row.addWidget(btn_pre_box)

        btn_pre_cinema = QPushButton("Cinema")
        btn_pre_cinema.clicked.connect(lambda: self.applyPreset("cinema"))
        control_row.addWidget(btn_pre_cinema)

        btn_pre_neon = QPushButton("Neon Pop")
        btn_pre_neon.clicked.connect(lambda: self.applyPreset("neon"))
        control_row.addWidget(btn_pre_neon)

        preview_layout.addLayout(control_row)
        splitter.addWidget(preview_container)

        # =====================================================================
        # RIGHT: Typography Editing & Export Controls (Scrollable)
        # =====================================================================
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFixedWidth(440)
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)

        # 1. Typography & Font Group
        font_group = QGroupBox("Typography & Font")
        font_form = QFormLayout(font_group)

        self.combo_font = QComboBox()
        self.combo_font.addItems(["Segoe UI", "Nirmala UI", "Arial", "Impact", "Trebuchet MS", "Verdana", "Montserrat"])
        self.combo_font.currentTextChanged.connect(self.onStyleChanged)
        font_form.addRow("Font Family:", self.combo_font)

        size_row = QHBoxLayout()
        self.slider_font_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_font_size.setRange(20, 80)
        self.slider_font_size.setValue(self.style.font_size)
        self.slider_font_size.valueChanged.connect(self.onFontSizeChanged)
        size_row.addWidget(self.slider_font_size)
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(20, 80)
        self.spin_font_size.setValue(self.style.font_size)
        self.spin_font_size.valueChanged.connect(self.slider_font_size.setValue)
        size_row.addWidget(self.spin_font_size)
        font_form.addRow("Font Size (pt):", size_row)

        style_checks = QHBoxLayout()
        self.chk_bold = QCheckBox("Bold")
        self.chk_bold.setChecked(self.style.is_bold)
        self.chk_bold.toggled.connect(self.onStyleChanged)
        style_checks.addWidget(self.chk_bold)
        self.chk_italic = QCheckBox("Italic")
        self.chk_italic.setChecked(self.style.is_italic)
        self.chk_italic.toggled.connect(self.onStyleChanged)
        style_checks.addWidget(self.chk_italic)
        font_form.addRow("Style:", style_checks)

        gap_row = QHBoxLayout()
        self.slider_line_gap = QSlider(Qt.Orientation.Horizontal)
        self.slider_line_gap.setRange(0, 40)
        self.slider_line_gap.setValue(getattr(self.style, 'line_gap', 8))
        self.slider_line_gap.valueChanged.connect(self.onLineGapChanged)
        gap_row.addWidget(self.slider_line_gap)
        self.spin_line_gap = QSpinBox()
        self.spin_line_gap.setRange(0, 40)
        self.spin_line_gap.setValue(getattr(self.style, 'line_gap', 8))
        self.spin_line_gap.valueChanged.connect(self.slider_line_gap.setValue)
        gap_row.addWidget(self.spin_line_gap)
        font_form.addRow("Line Gap / Spacing (px):", gap_row)

        sidebar_layout.addWidget(font_group)

        # 2. Colors & Highlight Beat Group
        color_group = QGroupBox("Color & Vocal Beat Highlight")
        color_form = QFormLayout(color_group)

        # Normal text color
        text_col_row = QHBoxLayout()
        self.btn_text_color = QPushButton("Pick Color")
        self.btn_text_color.setStyleSheet("background-color: #ffffff; color: #000000; font-weight: bold;")
        self.btn_text_color.clicked.connect(self.pickTextColor)
        text_col_row.addWidget(self.btn_text_color)
        color_form.addRow("Text Color:", text_col_row)

        # Active Word Highlight color
        hl_col_row = QHBoxLayout()
        self.btn_hl_color = QPushButton("Pick Highlight")
        self.btn_hl_color.setStyleSheet("background-color: #ffd700; color: #000000; font-weight: bold;")
        self.btn_hl_color.clicked.connect(self.pickHighlightColor)
        hl_col_row.addWidget(self.btn_hl_color)
        color_form.addRow("Active Word / Beat:", hl_col_row)

        # Background Box & Opacity
        self.chk_bg_box = QCheckBox("Enable Background Box")
        self.chk_bg_box.setChecked(self.style.bg_box_enabled)
        self.chk_bg_box.toggled.connect(self.onStyleChanged)
        color_form.addRow(self.chk_bg_box)

        bg_col_row = QHBoxLayout()
        self.btn_bg_color = QPushButton("Box Color")
        self.btn_bg_color.setStyleSheet("background-color: #0f0f0f; color: #ffffff;")
        self.btn_bg_color.clicked.connect(self.pickBgColor)
        bg_col_row.addWidget(self.btn_bg_color)
        color_form.addRow("Box Color:", bg_col_row)

        self.slider_bg_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_bg_opacity.setRange(0, 100)
        self.slider_bg_opacity.setValue(int(self.style.bg_opacity * 100))
        self.slider_bg_opacity.valueChanged.connect(self.onStyleChanged)
        color_form.addRow("Box Opacity (%):", self.slider_bg_opacity)

        sidebar_layout.addWidget(color_group)

        # 3. Stroke Outline & Shadow Group
        fx_group = QGroupBox("Outline Stroke & Drop Shadow")
        fx_form = QFormLayout(fx_group)

        stroke_row = QHBoxLayout()
        self.slider_stroke = QSlider(Qt.Orientation.Horizontal)
        self.slider_stroke.setRange(0, 10)
        self.slider_stroke.setValue(self.style.stroke_width)
        self.slider_stroke.valueChanged.connect(self.onStyleChanged)
        stroke_row.addWidget(self.slider_stroke)
        self.btn_stroke_col = QPushButton("Outline Color")
        self.btn_stroke_col.setStyleSheet("background-color: #000000; color: #ffffff;")
        self.btn_stroke_col.clicked.connect(self.pickStrokeColor)
        stroke_row.addWidget(self.btn_stroke_col)
        fx_form.addRow("Stroke Outline:", stroke_row)

        shadow_row = QHBoxLayout()
        self.slider_shadow = QSlider(Qt.Orientation.Horizontal)
        self.slider_shadow.setRange(0, 15)
        self.slider_shadow.setValue(self.style.shadow_offset)
        self.slider_shadow.valueChanged.connect(self.onStyleChanged)
        shadow_row.addWidget(self.slider_shadow)
        fx_form.addRow("Drop Shadow (px):", shadow_row)

        sidebar_layout.addWidget(fx_group)

        # 4. Placement & Alignment Group
        pos_group = QGroupBox("Caption Placement")
        pos_form = QFormLayout(pos_group)

        self.combo_pos = QComboBox()
        self.combo_pos.addItems(["Bottom", "Center", "Top", "Custom"])
        self.combo_pos.currentTextChanged.connect(self.onPositionChanged)
        pos_form.addRow("Vertical Position:", self.combo_pos)

        self.slider_v_offset = QSlider(Qt.Orientation.Horizontal)
        self.slider_v_offset.setRange(10, 95)
        self.slider_v_offset.setValue(self.style.vertical_offset_pct)
        self.slider_v_offset.valueChanged.connect(self.onStyleChanged)
        pos_form.addRow("Vertical Offset (%):", self.slider_v_offset)

        self.combo_align = QComboBox()
        self.combo_align.addItems(["Center", "Left", "Right"])
        self.combo_align.currentTextChanged.connect(self.onStyleChanged)
        pos_form.addRow("Text Alignment:", self.combo_align)

        sidebar_layout.addWidget(pos_group)

        # 5. Caption Animation & Motion Group
        anim_group = QGroupBox("Caption Animation & Motion")
        anim_form = QFormLayout(anim_group)

        self.combo_anim = QComboBox()
        self.combo_anim.addItems(["None", "Pop", "Fade", "Slide", "Jump", "Color Outline", "Smooth Blur"])
        self.combo_anim.currentTextChanged.connect(self.onStyleChanged)
        anim_form.addRow("Animation Style:", self.combo_anim)

        self.chk_anim_scope = QCheckBox("Apply to All Captions")
        self.chk_anim_scope.setChecked(True)
        self.chk_anim_scope.toggled.connect(self.onStyleChanged)
        anim_form.addRow("Animation Scope:", self.chk_anim_scope)

        lbl_scope_hint = QLabel("<span style='color: #a0aec0; font-size: 8pt;'>Uncheck to apply only to intro (starting) and outro (ending) captions.</span>")
        lbl_scope_hint.setWordWrap(True)
        anim_form.addRow(lbl_scope_hint)

        sidebar_layout.addWidget(anim_group)

        # 6. Export Settings & Actions Group
        export_group = QGroupBox("Video Export Options")
        export_layout = QVBoxLayout(export_group)

        export_form = QFormLayout()

        self.combo_export_mode = QComboBox()
        self.combo_export_mode.addItem("Burned-in Video (.mp4)", "mp4")
        self.combo_export_mode.addItem("Green Screen Background (.mp4)", "green_screen")
        self.combo_export_mode.addItem("Transparent Frames ZIP (.zip)", "transparent_zip")
        export_form.addRow("Output Format:", self.combo_export_mode)

        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["High", "Balanced", "Fast"])
        export_form.addRow("Quality Preset:", self.combo_quality)

        export_layout.addLayout(export_form)

        self.export_progress = QProgressBar()
        self.export_progress.setValue(0)
        self.export_progress.setVisible(False)
        export_layout.addWidget(self.export_progress)

        self.export_status_lbl = QLabel("")
        self.export_status_lbl.setStyleSheet("color: #63b3ed; font-size: 9pt;")
        export_layout.addWidget(self.export_status_lbl)

        self.btn_export = QPushButton("Export Video")
        self.btn_export.setStyleSheet("background-color: #38a169; color: #ffffff; font-weight: bold; font-size: 11pt; padding: 10px;")
        self.btn_export.clicked.connect(self.startExport)
        export_layout.addWidget(self.btn_export)

        sidebar_layout.addWidget(export_group)
        sidebar_layout.addStretch()

        sidebar_scroll.setWidget(sidebar_widget)
        splitter.addWidget(sidebar_scroll)

        main_layout.addWidget(splitter)

    # =========================================================================
    # Video Playback Logic
    # =========================================================================
    def togglePlay(self):
        if self.is_playing:
            self.is_playing = False
            self.play_timer.stop()
            if hasattr(self, 'audio_player') and self.audio_player:
                self.audio_player.pause()
            self.btn_play.setText("Play")
            self.btn_play.setStyleSheet("background-color: #2b6cb0; color: #ffffff; font-weight: bold; padding: 6px 14px;")
        else:
            self.is_playing = True
            interval_ms = max(15, int(1000.0 / (self.fps or 30.0)))
            self.play_timer.start(interval_ms)
            if hasattr(self, 'audio_player') and self.audio_player:
                pos_ms = int((self.current_frame / (self.fps or 30.0)) * 1000)
                self.audio_player.setPosition(pos_ms)
                self.audio_player.play()
            self.btn_play.setText("Pause")
            self.btn_play.setStyleSheet("background-color: #c53030; color: #ffffff; font-weight: bold; padding: 6px 14px;")

    def advanceFrame(self):
        if not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.current_frame = 0
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            if hasattr(self, 'audio_player') and self.audio_player:
                self.audio_player.setPosition(0)
            self.togglePlay()
            return

        self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        if self.current_frame >= self.total_frames:
            self.current_frame = 0
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.togglePlay()
            return

        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(self.current_frame)
        self.seek_slider.blockSignals(False)
        self.renderAndDisplayFrame(frame)

    def onSeekMoved(self, frame_no):
        self.current_frame = frame_no
        self.showCurrentFrame()

    def onSeekReleased(self):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        if hasattr(self, 'audio_player') and self.audio_player:
            pos_ms = int((self.current_frame / (self.fps or 30.0)) * 1000)
            self.audio_player.setPosition(pos_ms)
        self.showCurrentFrame()

    def seekRelative(self, sec_delta):
        frame_delta = int(sec_delta * self.fps)
        new_frame = max(0, min(self.total_frames - 1, self.current_frame + frame_delta))
        self.current_frame = new_frame
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        self.seek_slider.setValue(self.current_frame)
        self.showCurrentFrame()

    def showCurrentFrame(self):
        if not self.cap or not self.cap.isOpened():
            self.video_display.setText("Video preview not loaded. Check file path.")
            return

        try:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()
            if not ret or frame is None:
                return
            self.renderAndDisplayFrame(frame)
        except Exception as frame_err:
            print(f"[Video Preview Error]: {frame_err}")

    def renderAndDisplayFrame(self, frame):
        try:
            h, w = frame.shape[:2]
            current_sec = self.current_frame / (self.fps or 30.0)
            self.time_label.setText(f"{format_seconds(current_sec)} / {format_seconds(self.duration_sec)}")

            # Responsive preview scaling for ultra-smooth playback (max 960x540)
            disp_w = max(480, min(960, self.video_display.width()))
            disp_h = max(270, min(540, self.video_display.height()))
            if w > disp_w or h > disp_h:
                scale = min(disp_w / w, disp_h / h)
                preview_frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)
            else:
                preview_frame = frame

            # Render styled caption with active motion animation
            rendered_bgr = render_caption_frame(preview_frame, current_sec, self.segments, self.style, mode="normal")

            # Convert to QImage and QPixmap
            rh, rw, rch = rendered_bgr.shape
            bytes_per_line = rch * rw
            rgb = cv2.cvtColor(rendered_bgr, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, rw, rh, bytes_per_line, QImage.Format.Format_RGB888).copy()

            target_size = self.video_display.size()
            if target_size.width() > 10 and target_size.height() > 10:
                trans_mode = Qt.TransformationMode.FastTransformation if self.is_playing else Qt.TransformationMode.SmoothTransformation
                pixmap = QPixmap.fromImage(qimg).scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, trans_mode)
                self.video_display.setPixmap(pixmap)
        except Exception as frame_err:
            print(f"[Video Render Error]: {frame_err}")

    # =========================================================================
    # Style Customization Handlers
    # =========================================================================
    def onFontSizeChanged(self, val):
        self.spin_font_size.setValue(val)
        self.style.font_size = val
        self.showCurrentFrame()

    def onLineGapChanged(self, val):
        self.spin_line_gap.setValue(val)
        self.style.line_gap = val
        self.showCurrentFrame()

    def onPositionChanged(self, pos_text):
        self.style.position = pos_text
        if pos_text == "Custom":
            self.slider_v_offset.setEnabled(True)
        else:
            self.slider_v_offset.setEnabled(False)
            if pos_text == "Top":
                self.slider_v_offset.setValue(12)
            elif pos_text == "Center":
                self.slider_v_offset.setValue(50)
            else:
                self.slider_v_offset.setValue(82)
        self.onStyleChanged()

    def onStyleChanged(self):
        self.style.font_family = self.combo_font.currentText()
        self.style.font_size = self.slider_font_size.value()
        self.style.is_bold = self.chk_bold.isChecked()
        self.style.is_italic = self.chk_italic.isChecked()
        self.style.bg_box_enabled = self.chk_bg_box.isChecked()
        self.style.bg_opacity = self.slider_bg_opacity.value() / 100.0
        self.style.stroke_width = self.slider_stroke.value()
        self.style.shadow_offset = self.slider_shadow.value()
        self.style.vertical_offset_pct = self.slider_v_offset.value()
        self.style.alignment = self.combo_align.currentText()
        if hasattr(self, 'combo_anim'):
            self.style.animation = self.combo_anim.currentText()
        if hasattr(self, 'chk_anim_scope'):
            self.style.anim_scope_all = self.chk_anim_scope.isChecked()
        self.showCurrentFrame()

    def pickTextColor(self):
        col = QColorDialog.getColor(QColor(*self.style.text_color), self, "Select Text Color")
        if col.isValid():
            self.style.text_color = (col.red(), col.green(), col.blue())
            self.btn_text_color.setStyleSheet(f"background-color: {col.name()}; color: {'#000000' if col.lightness() > 128 else '#ffffff'};")
            self.showCurrentFrame()

    def pickHighlightColor(self):
        col = QColorDialog.getColor(QColor(*self.style.highlight_color), self, "Select Active Word Highlight Color")
        if col.isValid():
            self.style.highlight_color = (col.red(), col.green(), col.blue())
            self.btn_hl_color.setStyleSheet(f"background-color: {col.name()}; color: {'#000000' if col.lightness() > 128 else '#ffffff'};")
            self.showCurrentFrame()

    def pickBgColor(self):
        col = QColorDialog.getColor(QColor(*self.style.bg_color), self, "Select Background Box Color")
        if col.isValid():
            self.style.bg_color = (col.red(), col.green(), col.blue())
            self.btn_bg_color.setStyleSheet(f"background-color: {col.name()}; color: {'#000000' if col.lightness() > 128 else '#ffffff'};")
            self.showCurrentFrame()

    def pickStrokeColor(self):
        col = QColorDialog.getColor(QColor(*self.style.stroke_color), self, "Select Outline Stroke Color")
        if col.isValid():
            self.style.stroke_color = (col.red(), col.green(), col.blue())
            self.btn_stroke_col.setStyleSheet(f"background-color: {col.name()}; color: {'#000000' if col.lightness() > 128 else '#ffffff'};")
            self.showCurrentFrame()

    def applyPreset(self, name):
        if name == "tiktok":
            self.combo_font.setCurrentText("Impact")
            self.slider_font_size.setValue(44)
            self.chk_bold.setChecked(True)
            self.style.text_color = (255, 255, 255)
            self.style.highlight_color = (255, 220, 0) # Gold
            self.chk_bg_box.setChecked(False)
            self.slider_stroke.setValue(4)
            self.style.stroke_color = (0, 0, 0)
            self.slider_shadow.setValue(2)
            self.combo_pos.setCurrentText("Bottom")
            self.slider_v_offset.setValue(80)
            if hasattr(self, 'combo_anim'):
                self.combo_anim.setCurrentText("Pop")
        elif name == "box":
            self.combo_font.setCurrentText("Segoe UI")
            self.slider_font_size.setValue(36)
            self.chk_bold.setChecked(True)
            self.style.text_color = (255, 255, 255)
            self.style.highlight_color = (99, 179, 237) # Soft Blue
            self.chk_bg_box.setChecked(True)
            self.style.bg_color = (15, 23, 42)
            self.slider_bg_opacity.setValue(75)
            self.slider_stroke.setValue(0)
            self.slider_shadow.setValue(0)
            self.combo_pos.setCurrentText("Bottom")
            self.slider_v_offset.setValue(82)
            if hasattr(self, 'combo_anim'):
                self.combo_anim.setCurrentText("Fade")
        elif name == "cinema":
            self.combo_font.setCurrentText("Arial")
            self.slider_font_size.setValue(34)
            self.chk_bold.setChecked(False)
            self.style.text_color = (255, 245, 200) # Warm White
            self.style.highlight_color = (255, 215, 0)
            self.chk_bg_box.setChecked(False)
            self.slider_stroke.setValue(2)
            self.style.stroke_color = (0, 0, 0)
            self.slider_shadow.setValue(5)
            self.combo_pos.setCurrentText("Bottom")
            self.slider_v_offset.setValue(85)
            if hasattr(self, 'combo_anim'):
                self.combo_anim.setCurrentText("Smooth Blur")
        elif name == "neon":
            self.combo_font.setCurrentText("Trebuchet MS")
            self.slider_font_size.setValue(40)
            self.chk_bold.setChecked(True)
            self.style.text_color = (255, 255, 255)
            self.style.highlight_color = (0, 255, 255) # Electric Cyan
            self.chk_bg_box.setChecked(True)
            self.style.bg_color = (10, 10, 25)
            self.slider_bg_opacity.setValue(75)
            self.slider_stroke.setValue(4)
            self.style.stroke_color = (255, 0, 128) # Neon Magenta
            self.slider_shadow.setValue(3)
            self.combo_pos.setCurrentText("Bottom")
            self.slider_v_offset.setValue(82)
            if hasattr(self, 'combo_anim'):
                self.combo_anim.setCurrentText("Color Outline")

        self.onStyleChanged()

    # =========================================================================
    # Export Video Action
    # =========================================================================
    def startExport(self):
        if self.is_playing:
            self.togglePlay()

        mode = self.combo_export_mode.currentData()
        quality = self.combo_quality.currentText()

        ext_map = {
            "mp4": "MP4 Video (*.mp4)",
            "green_screen": "Green Screen MP4 (*.mp4)",
            "transparent_zip": "ZIP Archive (*.zip)"
        }
        default_name = f"captioned_{mode}_{int(time.time())}.{'zip' if mode == 'transparent_zip' else 'mp4'}"
        save_path, _ = QFileDialog.getSaveFileName(self, "Export Captioned Output", default_name, ext_map.get(mode, "All Files (*.*)"))

        if not save_path:
            return

        self.btn_export.setEnabled(False)
        self.export_progress.setVisible(True)
        self.export_progress.setValue(0)
        self.export_status_lbl.setText("Starting export...")

        self.export_worker = VideoExportWorker(self.video_path, self.segments, self.style, mode, quality, save_path)
        self.export_worker.progress.connect(self.export_progress.setValue)
        self.export_worker.status.connect(self.export_status_lbl.setText)

        def on_export_done(success, msg):
            self.btn_export.setEnabled(True)
            self.export_progress.setVisible(False)
            if success:
                self.export_status_lbl.setText("Export completed successfully!")
                QMessageBox.information(self, "Export Complete", msg)
            else:
                self.export_status_lbl.setText("Export failed.")
                QMessageBox.critical(self, "Export Error", msg)

        self.export_worker.finished.connect(on_export_done)
        self.export_worker.start()

    def closeEvent(self, event):
        if hasattr(self, 'play_timer') and self.play_timer.isActive():
            self.play_timer.stop()
        if self.is_playing:
            self.is_playing = False
        if self.cap:
            self.cap.release()
            self.cap = None
        event.accept()
