import io
import logging
from typing import Optional

from PIL import Image, ImageEnhance
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
        # Convert to grayscale for better OCR accuracy
        image = image.convert('L')

        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)

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
