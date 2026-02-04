import unittest
from unittest.mock import MagicMock
from PIL import Image
from src.services.ocr import _build_combined_lut

class TestOCRCombinedLUT(unittest.TestCase):
    def test_combined_lut_structure(self):
        """
        Test that _build_combined_lut returns a valid LUT list.
        """
        mock_thumb = MagicMock(spec=Image.Image)
        mock_thumb.width = 10
        mock_thumb.height = 10
        mock_thumb.histogram.return_value = [0] * 256 # Empty histogram

        lut = _build_combined_lut(mock_thumb, cutoff=2, contrast_factor=1.5)

        self.assertIsInstance(lut, list)
        self.assertEqual(len(lut), 256)
        self.assertTrue(all(isinstance(x, int) for x in lut))
        self.assertTrue(all(0 <= x <= 255 for x in lut))

    def test_combined_lut_logic(self):
        """
        Test that _build_combined_lut correctly calculates values based on histogram.
        """
        mock_thumb = MagicMock(spec=Image.Image)
        mock_thumb.width = 10
        mock_thumb.height = 10
        # 100 pixels total

        # Histogram:
        # 50 pixels at 100
        # 50 pixels at 200
        # This gives clear Autocontrast points: Low=100, High=200.
        hist = [0] * 256
        hist[100] = 50
        hist[200] = 50
        mock_thumb.histogram.return_value = hist

        # Expected AC behavior:
        # 100 -> 0
        # 200 -> 255
        # Scale = 2.55

        # Expected Mean behavior:
        # Mean of processed image = (0*50 + 255*50)/100 = 127.5

        # Expected Contrast behavior (factor 1.5):
        # z = 127.5 + 1.5 * (y - 127.5)
        # 0 -> 127.5 + 1.5 * (-127.5) = 127.5 - 191.25 = -63.75 -> 0
        # 255 -> 127.5 + 1.5 * (127.5) = 127.5 + 191.25 = 318.75 -> 255

        # Let's check a mid value.
        # Original 150.
        # AC: 150 -> (150-100)*2.55 = 127.5 -> 128
        # Contrast: 128 -> 127.5 + 1.5 * (128 - 127.5) = 127.5 + 0.75 = 128.25 -> 128

        lut = _build_combined_lut(mock_thumb, cutoff=2, contrast_factor=1.5)

        self.assertEqual(lut[100], 0)
        self.assertEqual(lut[200], 255)
        # Allow small rounding diff
        self.assertTrue(127 <= lut[150] <= 129)

    def test_flat_image(self):
        """
        Test that flat image results in expansion around the value.
        """
        mock_thumb = MagicMock(spec=Image.Image)
        mock_thumb.width = 10
        mock_thumb.height = 10

        # All pixels at 128
        hist = [0] * 256
        hist[128] = 100
        mock_thumb.histogram.return_value = hist

        # Low=128, High=128 -> AC is identity.
        # Mean = 128.
        # Contrast: z = 128 + 1.5 * (y - 128)

        # 128 -> 128
        # 130 -> 128 + 3 = 131
        # 126 -> 128 - 3 = 125

        lut = _build_combined_lut(mock_thumb, cutoff=2, contrast_factor=1.5)

        self.assertEqual(lut[128], 128)
        self.assertEqual(lut[130], 131)
        self.assertEqual(lut[126], 125)

if __name__ == "__main__":
    unittest.main()
