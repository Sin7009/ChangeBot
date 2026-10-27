from fastapi import FastAPI, UploadFile, File, HTTPException
from paddleocr import PaddleOCR
import numpy as np
from PIL import Image
import io
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ocr_service")

app = FastAPI(title="PaddleOCR GPU Service")

# Initialize PaddleOCR engine (Eager load)
logger.info("Initializing PaddleOCR engine with GPU support...")
try:
    ocr = PaddleOCR(use_textline_orientation=True, lang="ru", device="gpu")
    logger.info("PaddleOCR engine initialized successfully on GPU.")
except Exception as e:
    logger.error(f"Failed to initialize PaddleOCR engine on GPU: {e}", exc_info=True)
    # Fallback to CPU for safety (e.g., if running in environments without CUDA drivers during setup)
    try:
        logger.info("Retrying initialization with CPU fallback...")
        ocr = PaddleOCR(use_textline_orientation=True, lang="ru", device="cpu")
        logger.info("PaddleOCR engine initialized successfully on CPU.")
    except Exception as ex:
        logger.critical(f"Critical error: Failed to initialize PaddleOCR on CPU fallback: {ex}", exc_info=True)
        raise ex

@app.post("/ocr")
async def perform_ocr(file: UploadFile = File(...)):
    """
    Accepts an image file, runs PaddleOCR, and returns the joined recognized text.
    """
    try:
        content = await file.read()
        image = Image.open(io.BytesIO(content))
        
        # Convert to RGB (standard format for PaddleOCR)
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        img_np = np.array(image)
        
        # Run OCR
        result = ocr.predict(img_np)
        
        texts = []
        if result and len(result) > 0:
            texts = result[0].get("rec_texts", [])
                     
        recognized_text = "\n".join(texts)
        return {"text": recognized_text}
    except Exception as e:
        logger.error(f"Error during OCR processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
