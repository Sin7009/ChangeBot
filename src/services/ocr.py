import io
import logging
from typing import Optional

from PIL import Image, ImageEnhance, ImageOps
import pytesseract

logger = logging.getLogger(__name__)

def image_to_text(image_bytes: bytes) -> Optional[str]:
    """
    Extracts text from an image byte stream using Tesseract OCR.

    Args:
        image_bytes: The image data in bytes.

    Returns:
        The extracted text as a string, or None if extraction fails or no text is found.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))

        # 1. Resize if too small (upscaling helps Tesseract detect characters)
        width, height = image.size
        # Target width ~1500-2000 for good OCR.
        # If the image is a screenshot, it might be e.g. 500px wide.
        if width < 1000:
            scale_factor = 2 if width > 500 else 3
            new_size = (width * scale_factor, height * scale_factor)
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        # 2. Convert to grayscale for better OCR accuracy
        image = image.convert('L')

        # 3. Enhance Contrast
        # Auto-contrast is often better than fixed factor for varying lighting conditions
        image = ImageOps.autocontrast(image, cutoff=2) # cutoff ignores top/bottom 2% of histogram

        # Additional fixed contrast boost can still help separate faint text from background
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        # 4. Sharpen (helps define edges for Tesseract)
        sharpness = ImageEnhance.Sharpness(image)
        image = sharpness.enhance(2.0)

        # Configure Tesseract:
        # -l rus+eng: Support Russian and English
        # --oem 3: Default OCR Engine Mode
        # --psm 6: Assume a single uniform block of text
        config = r'-l rus+eng --oem 3 --psm 6'

        text = pytesseract.image_to_string(image, config=config)

        if not text:
            return None

        cleaned_text = text.strip()

        if not cleaned_text:
            return None

        return cleaned_text

    except Exception as e:
        logger.error(f"Error during OCR processing: {e}")
        return None
