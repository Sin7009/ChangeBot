import unittest
from unittest.mock import MagicMock
from PIL import Image
from src.services.ocr import _fast_autocontrast

class TestOCRFastAutocontrast(unittest.TestCase):
    def test_fast_autocontrast_stretches_contrast(self):
        """
        Test that _fast_autocontrast applies a LUT that stretches contrast.
        """
        # Create a mock image
        mock_image = MagicMock(spec=Image.Image)
        mock_image.point.return_value = "processed_image"

        # Create a mock thumb
        mock_thumb = MagicMock(spec=Image.Image)
        mock_thumb.width = 10
        mock_thumb.height = 10
        # 100 pixels total

        # Mock histogram:
        # 0-50: 0
        # 51-100: scattered
        # 100-200: 0
        # 201-255: scattered

        # To make it simple:
        # 50 pixels at value 100
        # 50 pixels at value 200
        hist = [0] * 256
        hist[100] = 50
        hist[200] = 50

        mock_thumb.histogram.return_value = hist

        # Cutoff = 2% (2 pixels)
        # Low should be 100. High should be 200.
        # Scale = 255 / (200 - 100) = 2.55
        # Offset = -100 * 2.55 = -255

        # Value 100 -> 100 * 2.55 - 255 = 0
        # Value 150 -> 150 * 2.55 - 255 = 382.5 - 255 = 127.5
        # Value 200 -> 200 * 2.55 - 255 = 510 - 255 = 255

        result = _fast_autocontrast(mock_image, mock_thumb, cutoff=2)

        self.assertEqual(result, "processed_image")
        mock_image.point.assert_called_once()

        # Inspect the LUT passed to point()
        lut = mock_image.point.call_args[0][0]
        self.assertEqual(len(lut), 256)

        # Check specific values
        self.assertEqual(lut[100], 0)
        self.assertEqual(lut[200], 255)
        self.assertTrue(120 <= lut[150] <= 135) # Approx 127/128

    def test_fast_autocontrast_flat_image(self):
        """
        Test that _fast_autocontrast returns original image if histogram is flat (high <= low).
        """
        mock_image = MagicMock(spec=Image.Image)
        mock_thumb = MagicMock(spec=Image.Image)
        mock_thumb.width = 10
        mock_thumb.height = 10

        # All pixels at 128
        hist = [0] * 256
        hist[128] = 100
        mock_thumb.histogram.return_value = hist

        # Low = 128, High = 128

        result = _fast_autocontrast(mock_image, mock_thumb, cutoff=2)

        # Should return original image without calling point()
        self.assertEqual(result, mock_image)
        mock_image.point.assert_not_called()

if __name__ == "__main__":
    unittest.main()
