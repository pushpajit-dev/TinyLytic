"""
TinyLytic Vision & OCR Engine
Provides OpenCV (cv2) computer vision processing, image OCR, and video slide/scene-change timestamp extraction.
"""

import os
import sys
import tempfile
from core_engine import format_seconds

# OpenCV verification
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False
    cv2 = None
    np = None

# Tesseract verification
try:
    import pytesseract
    HAS_PYTESSERACT = True

    # Windows Tesseract standard installation locations
    standard_tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for path in standard_tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break
except Exception:
    HAS_PYTESSERACT = False
    pytesseract = None


def preprocess_image_for_ocr(image):
    """Enhance image contrast, grayscale, and thresholding for clean OCR."""
    if not HAS_CV2 or image is None:
        return image

    # 1. Grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # 2. Rescale if small
    h, w = gray.shape[:2]
    if w < 1000:
        scale = 1000 / w
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

    # 3. Bilateral filter to smooth while preserving edges
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)

    # 4. Adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
    )

    return thresh


def perform_image_ocr(image_path, lang="eng"):
    """
    Extract text from an image file using OpenCV + OCR.
    Returns: {"text": str, "success": bool, "message": str}
    """
    if not HAS_CV2:
        return {"text": "", "success": False, "message": "OpenCV (cv2) is not installed."}

    if not os.path.exists(image_path):
        return {"text": "", "success": False, "message": f"File not found: {image_path}"}

    try:
        # Load image via cv2 with unicode path support
        img_array = np.fromfile(image_path, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None:
            return {"text": "", "success": False, "message": "Failed to decode image file."}

        preprocessed = preprocess_image_for_ocr(img)

        extracted_text = ""
        # 1. Try pytesseract if available
        if HAS_PYTESSERACT:
            try:
                # Configure PSM 3 (fully automatic page segmentation)
                custom_config = r'--oem 3 --psm 3'
                extracted_text = pytesseract.image_to_string(preprocessed, lang=lang, config=custom_config).strip()
            except Exception as te:
                # Try raw image if preprocessed fails
                try:
                    extracted_text = pytesseract.image_to_string(img, lang=lang).strip()
                except Exception:
                    pass

        # 2. Fallback: text region contour detection with OpenCV
        if not extracted_text:
            contours_detected = detect_text_contours(preprocessed)
            if contours_detected > 0:
                return {
                    "text": f"[OpenCV Text Region Detection]\nDetected {contours_detected} potential text blocks.\n(Note: To extract character text, ensure Tesseract OCR is installed on your PC).",
                    "success": True,
                    "message": "Text regions detected via OpenCV."
                }
            else:
                return {"text": "", "success": True, "message": "No text detected in image."}

        return {
            "text": extracted_text,
            "success": True,
            "message": "OCR successfully extracted text."
        }

    except Exception as e:
        return {"text": "", "success": False, "message": f"Error performing OCR: {str(e)}"}


def detect_text_contours(thresh_img):
    """Detect potential text bounding boxes using OpenCV morphological operations."""
    if not HAS_CV2 or thresh_img is None:
        return 0

    try:
        # Morphological dilation with rectangular kernel
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 18))
        dilation = cv2.dilate(thresh_img, rect_kernel, iterations=1)
        # Invert if white background
        inverted = cv2.bitwise_not(dilation)
        contours, _ = cv2.findContours(inverted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        valid_contours = [c for c in contours if cv2.contourArea(c) > 100]
        return len(valid_contours)
    except Exception:
        return 0


def analyze_video_slides(video_path, progress_callback=None, interval_seconds=4, threshold=30.0):
    """
    Extract slide transition timestamps and on-screen text from video using OpenCV & OCR.
    Yields or returns a list of chapters with timestamps:
    [{"timestamp": "01:25", "seconds": 85, "title": "Introduction to Architecture"}]
    """
    if not HAS_CV2:
        raise RuntimeError("OpenCV (cv2) is required for video slide analysis.")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_sec = total_frames / fps if fps > 0 else 0

    sample_step_frames = int(fps * interval_seconds)
    if sample_step_frames < 1:
        sample_step_frames = 1

    slide_events = []
    prev_gray = None
    slide_index = 1
    current_frame = 0

    while cap.isOpened():
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        timestamp_sec = current_frame / fps
        time_str = format_seconds(timestamp_sec)

        # Grayscale downscaled frame for comparison
        small = cv2.resize(frame, (320, 180))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        is_new_slide = False
        if prev_gray is None:
            # First frame is always a slide/start
            is_new_slide = True
        else:
            # Compute frame difference
            diff = cv2.absdiff(prev_gray, gray)
            diff_score = np.mean(diff)
            if diff_score >= threshold:
                is_new_slide = True

        if is_new_slide:
            prev_gray = gray
            # Extract OCR title from top 30% of slide
            h, w = frame.shape[:2]
            header_crop = frame[0:int(h * 0.35), 0:w]
            header_text = ""

            if HAS_PYTESSERACT:
                try:
                    prep = preprocess_image_for_ocr(header_crop)
                    raw_text = pytesseract.image_to_string(prep, config=r'--oem 3 --psm 6').strip()
                    first_line = raw_text.splitlines()[0] if raw_text else ""
                    # Keep clean characters
                    header_text = " ".join(first_line.split())[:80]
                except Exception:
                    pass

            if not header_text:
                header_text = f"Slide {slide_index}"

            slide_events.append({
                "slide_number": slide_index,
                "seconds": round(timestamp_sec, 1),
                "timestamp": time_str,
                "header": header_text
            })
            slide_index += 1

        current_frame += sample_step_frames
        if progress_callback and total_frames > 0:
            percent = int((current_frame / total_frames) * 100)
            progress_callback(min(percent, 99))

    cap.release()

    if progress_callback:
        progress_callback(100)

    # Format result into chapter timestamps
    formatted_lines = []
    for i, slide in enumerate(slide_events):
        start_time = slide["timestamp"]
        end_time = slide_events[i + 1]["timestamp"] if i + 1 < len(slide_events) else format_seconds(duration_sec)
        formatted_lines.append(f"{start_time}-{end_time} Chapter {slide['slide_number']}: {slide['header']}")

    return {
        "slides": slide_events,
        "formatted_text": "\n".join(formatted_lines),
        "total_slides": len(slide_events)
    }
