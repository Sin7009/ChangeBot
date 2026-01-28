import unittest
from unittest.mock import MagicMock, patch
from src.services.ocr import image_to_text

class TestOCROptimization(unittest.TestCase):
    def setUp(self):
        # Create a dummy image bytes
        self.image_bytes = b"fake_image_data"

    @patch("src.services.ocr.Image.open")
    @patch("src.services.ocr.pytesseract.image_to_string")
    def test_avoids_convert_if_already_L(self, mock_ocr, mock_open):
        """
        Test that image.convert('L') is NOT called if image is already in 'L' mode.
        """
        # Setup mock image
        mock_image = MagicMock()
        mock_image.mode = 'L'
        mock_image.size = (100, 100)
        mock_image.format = 'JPEG'

        # When resize is called (for thumbnail or scaling), return a new mock
        # This prevents ImageStat error
        mock_resized = MagicMock()
        mock_resized.mode = 'L'
        mock_resized.histogram.return_value = [0]*256 # Mock histogram for ImageStat
        # Mock getbbox for ImageStat internal checks or similar if needed,
        # but ImageStat(thumb) mainly needs histogram or pixel access.
        # Actually ImageStat.Stat(image) calls image.histogram() or uses pixel access.
        # Let's mock ImageStat.Stat as well to avoid deep PIL mocking.

        mock_image.resize.return_value = mock_resized

        mock_open.return_value = mock_image
        mock_ocr.return_value = "text"

        with patch("src.services.ocr.ImageStat.Stat") as mock_stat:
            mock_stat.return_value.mean = [200] # Light image

            # Run function
            image_to_text(self.image_bytes)

        # Verify convert was NOT called
        mock_image.convert.assert_not_called()

    @patch("src.services.ocr.Image.open")
    @patch("src.services.ocr.pytesseract.image_to_string")
    def test_calls_convert_if_RGB(self, mock_ocr, mock_open):
        """
        Test that image.convert('L') IS called if image is in 'RGB' mode.
        """
        mock_image = MagicMock()
        mock_image.mode = 'RGB'
        mock_image.size = (100, 100)
        mock_image.format = 'PNG'

        mock_converted = MagicMock()
        mock_converted.mode = 'L'
        mock_converted.size = (100, 100)

        mock_resized = MagicMock()
        mock_resized.mode = 'L'

        mock_image.convert.return_value = mock_converted
        mock_converted.resize.return_value = mock_resized

        mock_open.return_value = mock_image
        mock_ocr.return_value = "text"

        with patch("src.services.ocr.ImageStat.Stat") as mock_stat:
            mock_stat.return_value.mean = [200]

            image_to_text(self.image_bytes)

        mock_image.convert.assert_called_with('L')

if __name__ == "__main__":
    unittest.main()
