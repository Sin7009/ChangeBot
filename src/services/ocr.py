import io
import logging
from typing import Optional

from PIL import Image, ImageEnhance, ImageOps, ImageStat
import pytesseract

logger = logging.getLogger(__name__)

def image_to_text(image_bytes: bytes) -> Optional[str]:
    """
    Extracts text from an image byte stream using Tesseract OCR.
    Includes preprocessing for dark mode and low contrast.

    Args:
        image_bytes: The image data in bytes.

    Returns:
        The extracted text as a string, or None if extraction fails or no text is found.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Log original size
        width, height = image.size
        logger.info(f"OCR Request: Image size {width}x{height}")

        # 1. Convert to grayscale for better OCR accuracy
        # Doing this first speeds up subsequent operations (resize, stats) by working on 1 channel instead of 3.
        image = image.convert('L')

        # 2. Detect Dark Mode and Invert
        # Calculate mean brightness
        stat = ImageStat.Stat(image)
        avg_brightness = stat.mean[0]

        if avg_brightness < 128:
            logger.info(f"Image is dark (avg={avg_brightness:.2f}), inverting...")
            image = ImageOps.invert(image)
        else:
            logger.info(f"Image is light (avg={avg_brightness:.2f}), skipping inversion.")

        # 3. Resize if too small (upscaling helps Tesseract detect characters)
        if width < 1000:
            scale_factor = 2 if width > 500 else 3
            new_size = (width * scale_factor, height * scale_factor)
            # Use BICUBIC instead of LANCZOS for faster processing (~1.9x speedup)
            # while maintaining sufficient quality for OCR
            image = image.resize(new_size, Image.Resampling.BICUBIC)
            logger.info(f"Resized image to {new_size}")

        # 4. Enhance Contrast
        # Auto-contrast is often better than fixed factor for varying lighting conditions
        image = ImageOps.autocontrast(image, cutoff=2) # cutoff ignores top/bottom 2% of histogram

        # Additional fixed contrast boost can still help separate faint text from background
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        # 5. Sharpen (helps define edges for Tesseract)
        sharpness = ImageEnhance.Sharpness(image)
        image = sharpness.enhance(2.0)

        # Configure Tesseract:
        # -l rus+eng: Support Russian and English
        # --oem 3: Default OCR Engine Mode
        # --psm 6: Assume a single uniform block of text
        config = r'-l rus+eng --oem 3 --psm 6'

        text = pytesseract.image_to_string(image, config=config)

        if not text:
            logger.info("OCR Result: No text extracted.")
            return None

        cleaned_text = text.strip()

        if not cleaned_text:
            logger.info("OCR Result: Text was empty after stripping.")
            return None

        # Log the beginning of the text
        log_text = cleaned_text.replace('\n', ' ')
        if len(log_text) > 100:
            log_text = log_text[:100] + "..."
        logger.info(f"OCR Result: {log_text}")

        return cleaned_text

    except Exception as e:
        logger.error(f"Error during OCR processing: {e}", exc_info=True)
        return None
