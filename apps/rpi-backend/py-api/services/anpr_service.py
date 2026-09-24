"""
ANPR (Automatic Number Plate Recognition) Service
Processes vehicle license plate images and detects plate text
"""

from __future__ import annotations

import logging
import base64
import io
import asyncio
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
import tempfile

# Try to import OCR library
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# Try to import image processing
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ANPRService:
    """Automatic Number Plate Recognition service for detecting vehicle license plates"""

    # Czech plate format: 2 letters, 4 digits, 2 letters (e.g., ABC 1234 XY)
    CZECH_PLATE_PATTERN = r"^[A-Z]{2}\d{3,5}[A-Z]{2}$"

    def __init__(self, model_dir: Optional[str] = None, languages: list = None):
        """
        Initialize ANPR service

        Args:
            model_dir: Directory for caching OCR models
            languages: List of languages for OCR (default: ['cs', 'en'])
        """
        self.model_dir = model_dir or str(Path.home() / ".cache" / "anpr_models")
        self.languages = languages or ["cs", "en"]
        self.reader = None
        self.ready = False

        if EASYOCR_AVAILABLE:
            self._init_ocr()
        else:
            logger.warning("EasyOCR not available. Install with: pip install easyocr")

    def _init_ocr(self):
        """Initialize EasyOCR reader in background"""
        try:
            self.reader = easyocr.Reader(self.languages, gpu=False, model_storage_directory=self.model_dir)
            self.ready = True
            logger.info(f"ANPR OCR service ready (languages: {self.languages})")
        except Exception as e:
            logger.error(f"Failed to initialize OCR reader: {e}")
            self.ready = False

    async def process_image(self, image_data: bytes, image_format: str = "jpeg") -> Dict[str, Any]:
        """
        Process image to detect license plates

        Args:
            image_data: Raw image bytes
            image_format: Image format ('jpeg', 'png', etc.)

        Returns:
            Dict with detected plates, confidence scores, and metadata
        """
        if not self.ready:
            return {
                "status": "error",
                "message": "ANPR service not ready. Install: pip install easyocr opencv-python",
                "plates": [],
            }

        try:
            # Decode image
            if not CV2_AVAILABLE:
                return {
                    "status": "error",
                    "message": "OpenCV not available. Install with: pip install opencv-python",
                    "plates": [],
                }

            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                return {
                    "status": "error",
                    "message": "Failed to decode image",
                    "plates": [],
                }

            # Run OCR in thread pool (doesn't block event loop)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._detect_plates_sync,
                img
            )

            return result

        except Exception as e:
            logger.error(f"Error processing image: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "plates": [],
            }

    def _detect_plates_sync(self, img: np.ndarray) -> Dict[str, Any]:
        """
        Synchronous plate detection (runs in executor)

        Args:
            img: OpenCV image

        Returns:
            Dict with detected plates
        """
        try:
            # Preprocess image for better OCR
            preprocessed = self._preprocess_image(img)

            # Run OCR
            results = self.reader.readtext(preprocessed)

            # Filter and parse results
            plates = []
            for detection in results:
                bbox, text, confidence = detection
                text = text.strip().upper()

                # Filter by confidence
                if confidence < 0.5:
                    continue

                # Check if it looks like a plate
                cleaned_text = self._clean_plate_text(text)
                if self._is_valid_plate(cleaned_text):
                    plates.append({
                        "text": cleaned_text,
                        "raw_text": text,
                        "confidence": float(confidence),
                        "bbox": [[float(p[0]), float(p[1])] for p in bbox],
                    })

            # Sort by confidence
            plates.sort(key=lambda p: p["confidence"], reverse=True)

            return {
                "status": "success",
                "plates": plates,
                "plate_count": len(plates),
                "timestamp": datetime.now().isoformat(),
                "image_size": {"width": img.shape[1], "height": img.shape[0]},
            }

        except Exception as e:
            logger.error(f"Error in plate detection: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "plates": [],
            }

    @staticmethod
    def _preprocess_image(img: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better plate detection

        Args:
            img: OpenCV image

        Returns:
            Preprocessed image
        """
        if not CV2_AVAILABLE:
            return img

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply contrast enhancement (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Apply sharpening kernel
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)

        return sharpened

    @staticmethod
    def _clean_plate_text(text: str) -> str:
        """
        Clean OCR text to match plate format

        Args:
            text: Raw OCR text

        Returns:
            Cleaned text
        """
        # Remove common OCR errors: O->0, I->1, l->1
        text = text.replace("O", "0").replace("I", "1").replace("l", "1")

        # Remove spaces
        text = text.replace(" ", "")

        # Remove non-alphanumeric
        text = "".join(c for c in text if c.isalnum())

        return text.upper()

    def _is_valid_plate(self, text: str) -> bool:
        """
        Check if text matches Czech plate pattern

        Czech format: 2 letters, 3-5 digits, 2 letters
        Examples: AB12345CD, AB1234CD

        Args:
            text: Cleaned text

        Returns:
            True if valid plate format
        """
        import re

        if len(text) < 7 or len(text) > 9:
            return False

        # Check format: 2 letters + 3-5 digits + 2 letters
        pattern = re.compile(r"^[A-Z]{2}\d{3,5}[A-Z]{2}$")
        return bool(pattern.match(text))

    def format_plate_for_db(self, text: str) -> str:
        """
        Format plate text for database storage (canonical format)

        Args:
            text: Plate text

        Returns:
            Formatted text (e.g., "AB 12345 CD")
        """
        if len(text) < 7:
            return text

        # Format: 2 letters, space, 3-5 digits, space, 2 letters
        letters_prefix = text[:2]
        digits = text[2:-2]
        letters_suffix = text[-2:]

        return f"{letters_prefix} {digits} {letters_suffix}"


# Global service instance
_anpr_service: Optional[ANPRService] = None


def get_anpr_service() -> ANPRService:
    """Get or create global ANPR service instance"""
    global _anpr_service
    if _anpr_service is None:
        _anpr_service = ANPRService()
    return _anpr_service


async def process_image_data(image_data: bytes, image_format: str = "jpeg") -> Dict[str, Any]:
    """Process image and return detected plates"""
    service = get_anpr_service()
    return await service.process_image(image_data, image_format)
