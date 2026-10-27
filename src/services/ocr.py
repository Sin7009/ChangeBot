import io
import logging
import os
from typing import Optional, Union
import aiohttp

logger = logging.getLogger(__name__)

OCR_SERVICE_URL = os.getenv("OCR_SERVICE_URL", "http://ocr-service:8000/ocr")

async def image_to_text(image_input: Union[bytes, io.BytesIO]) -> Optional[str]:
    """
    Extracts text from an image by sending it to the external PaddleOCR service.

    Args:
        image_input: The image data as bytes or io.BytesIO.

    Returns:
        The extracted text as a string, or None if extraction fails or no text is found.
    """
    try:
        # Get raw bytes
        if isinstance(image_input, io.BytesIO):
            image_bytes = image_input.getvalue()
        else:
            image_bytes = image_input

        logger.info(f"Sending OCR Request to {OCR_SERVICE_URL} (size: {len(image_bytes)} bytes)")

        # Send image to the ocr-service microservice via HTTP POST
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field(
                'file',
                image_bytes,
                filename='image.jpg',
                content_type='image/jpeg'
            )
            
            # Use a timeout of 30.0s for the request
            async with session.post(OCR_SERVICE_URL, data=data, timeout=30.0) as response:
                if response.status == 200:
                    result = await response.json()
                    text = result.get("text")
                    if text:
                        cleaned = text.strip()
                        if cleaned:
                            # Log the beginning of the extracted text
                            log_text = cleaned.replace('\n', ' ')
                            if len(log_text) > 100:
                                log_text = log_text[:100] + "..."
                            logger.info(f"OCR Result: {log_text}")
                            return cleaned
                    logger.info("OCR Result: No text extracted.")
                    return None
                else:
                    logger.error(f"OCR service returned error status {response.status}")
                    return None

    except Exception as e:
        logger.error(f"Error during OCR service request: {e}", exc_info=True)
        return None
