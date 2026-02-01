import unittest
from unittest.mock import MagicMock
from PIL import Image
from src.services.ocr import _build_combined_lut

class TestOCRCombinedLUT(unittest.TestCase):
    def test_combined_lut_stretches_and_enhances(self):
        """
        Test that _build_combined_lut produces a LUT that stretches contrast
        and applies enhancement centered on mean.
        """
        # Create a mock thumb
        mock_thumb = MagicMock(spec=Image.Image)
        mock_thumb.width = 10
        mock_thumb.height = 10
        # 100 pixels total

        # Mock histogram:
        # 50 pixels at value 100
        # 50 pixels at value 200
        hist = [0] * 256
        hist[100] = 50
        hist[200] = 50

        mock_thumb.histogram.return_value = hist

        # Expected Math:
        # Low=100, High=200 -> Scale=2.55, Offset=-255
        # Autocontrast values: 100->0, 200->255
        # Mean of autocontrasted image: (50*0 + 50*255)/100 = 127.5
        # Contrast enhance (factor 1.5):
        # 0 -> 127.5 + (0 - 127.5)*1.5 = 127.5 - 191.25 = -63.75 -> 0
        # 255 -> 127.5 + (255 - 127.5)*1.5 = 127.5 + 191.25 = 318.75 -> 255

        lut = _build_combined_lut(mock_thumb, cutoff=2, contrast_factor=1.5)

        self.assertEqual(len(lut), 256)
        self.assertEqual(lut[100], 0)
        self.assertEqual(lut[200], 255)

        # Test a value in the middle: 150
        # AC value: 150*2.55 - 255 = 127.5
        # Enhance: 127.5 + (127.5 - 127.5)*1.5 = 127.5 -> 127 or 128
        self.assertTrue(126 <= lut[150] <= 129)

    def test_combined_lut_flat_image(self):
        """
        Test that _build_combined_lut handles flat image correctly.
        """
        mock_thumb = MagicMock(spec=Image.Image)
        mock_thumb.width = 10
        mock_thumb.height = 10

        # All pixels at 128
        hist = [0] * 256
        hist[128] = 100
        mock_thumb.histogram.return_value = hist

        # Low=128, High=128 -> Scale=1.0, Offset=0.0
        # AC Mean = 128
        # Enhance: val = 128 + (val - 128)*1.5
        # For val=128 -> 128

        lut = _build_combined_lut(mock_thumb, cutoff=2, contrast_factor=1.5)

        self.assertEqual(lut[128], 128)

        # Check that it still tries to enhance contrast for other values
        # e.g. 130 -> 128 + (130-128)*1.5 = 128 + 3 = 131
        self.assertEqual(lut[130], 131)

if __name__ == "__main__":
    unittest.main()
