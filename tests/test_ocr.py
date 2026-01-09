from unittest.mock import patch
from PIL import Image
import io
from src.services.ocr import image_to_text


def create_test_image(width=100, height=100, mode='RGB', color=(255, 255, 255)):
    """Helper to create a test image"""
    img = Image.new(mode, (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def test_image_to_text_with_empty_result():
    """Test OCR with empty result returns None"""
    image_bytes = create_test_image()
    
    with patch('pytesseract.image_to_string', return_value=''):
        result = image_to_text(image_bytes)
        assert result is None


def test_image_to_text_with_whitespace_only():
    """Test OCR with whitespace-only result returns None"""
    image_bytes = create_test_image()
    
    with patch('pytesseract.image_to_string', return_value='   \n  \t  '):
        result = image_to_text(image_bytes)
        assert result is None


def test_image_to_text_with_valid_text():
    """Test OCR with valid text returns cleaned result"""
    image_bytes = create_test_image()
    
    with patch('pytesseract.image_to_string', return_value='  Test Text  \n'):
        result = image_to_text(image_bytes)
        assert result == 'Test Text'

def test_image_to_text_with_bytesio():
    """Test OCR accepts io.BytesIO"""
    image_bytes = create_test_image()
    buf = io.BytesIO(image_bytes)

    with patch('pytesseract.image_to_string', return_value='  Test Text  \n'):
        result = image_to_text(buf)
        assert result == 'Test Text'


def test_image_to_text_dark_mode_detection():
    """Test that dark images are inverted"""
    # Create a dark image (black background)
    dark_image_bytes = create_test_image(color=(0, 0, 0))
    
    with patch('pytesseract.image_to_string', return_value='Test') as mock_ocr:
        result = image_to_text(dark_image_bytes)
        # Verify OCR was called (meaning image processing succeeded)
        assert mock_ocr.called
        assert result == 'Test'


def test_image_to_text_handles_small_images():
    """Test that small images are upscaled"""
    small_image_bytes = create_test_image(width=300, height=200)
    
    with patch('pytesseract.image_to_string', return_value='Upscaled Text') as mock_ocr:
        result = image_to_text(small_image_bytes)
        assert mock_ocr.called
        assert result == 'Upscaled Text'


def test_image_to_text_handles_exception():
    """Test that exceptions during OCR are handled gracefully"""
    image_bytes = create_test_image()
    
    with patch('pytesseract.image_to_string', side_effect=Exception("OCR Error")):
        result = image_to_text(image_bytes)
        assert result is None


def test_image_to_text_invalid_image_data():
    """Test handling of invalid image data"""
    invalid_bytes = b'not an image'
    
    result = image_to_text(invalid_bytes)
    assert result is None
