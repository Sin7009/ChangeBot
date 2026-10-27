import pytest
from unittest.mock import AsyncMock, patch
import io
from src.services.ocr import image_to_text

def create_test_image(width=100, height=100, mode='RGB', color=(255, 255, 255)):
    """Helper to create a test image"""
    from PIL import Image
    img = Image.new(mode, (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

class MockResponse:
    def __init__(self, status, json_data):
        self.status = status
        self._json_data = json_data

    async def json(self):
        return self._json_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.mark.asyncio
async def test_image_to_text_with_empty_result():
    """Test OCR with empty result returns None"""
    image_bytes = create_test_image()
    mock_resp = MockResponse(200, {"text": ""})
    
    with patch('aiohttp.ClientSession.post', return_value=mock_resp):
        result = await image_to_text(image_bytes)
        assert result is None

@pytest.mark.asyncio
async def test_image_to_text_with_whitespace_only():
    """Test OCR with whitespace-only result returns None"""
    image_bytes = create_test_image()
    mock_resp = MockResponse(200, {"text": "   \n  \t  "})
    
    with patch('aiohttp.ClientSession.post', return_value=mock_resp):
        result = await image_to_text(image_bytes)
        assert result is None

@pytest.mark.asyncio
async def test_image_to_text_with_valid_text():
    """Test OCR with valid text returns cleaned result"""
    image_bytes = create_test_image()
    mock_resp = MockResponse(200, {"text": "  Test Text  \n"})
    
    with patch('aiohttp.ClientSession.post', return_value=mock_resp):
        result = await image_to_text(image_bytes)
        assert result == 'Test Text'

@pytest.mark.asyncio
async def test_image_to_text_with_bytesio():
    """Test OCR accepts io.BytesIO"""
    image_bytes = create_test_image()
    buf = io.BytesIO(image_bytes)
    mock_resp = MockResponse(200, {"text": "  Test Text  \n"})

    with patch('aiohttp.ClientSession.post', return_value=mock_resp):
        result = await image_to_text(buf)
        assert result == 'Test Text'

@pytest.mark.asyncio
async def test_image_to_text_handles_error_status():
    """Test OCR handles non-200 HTTP status gracefully"""
    image_bytes = create_test_image()
    mock_resp = MockResponse(500, {})
    
    with patch('aiohttp.ClientSession.post', return_value=mock_resp):
        result = await image_to_text(image_bytes)
        assert result is None

@pytest.mark.asyncio
async def test_image_to_text_handles_exception():
    """Test that exceptions during OCR HTTP request are handled gracefully"""
    image_bytes = create_test_image()
    
    with patch('aiohttp.ClientSession.post', side_effect=Exception("Connection Error")):
        result = await image_to_text(image_bytes)
        assert result is None
