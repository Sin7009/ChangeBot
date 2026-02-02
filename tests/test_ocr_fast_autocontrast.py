import unittest
from unittest.mock import MagicMock
from PIL import Image
from src.services.ocr import _build_combined_lut

class TestOCRCombinedLUT(unittest.TestCase):
    def test_combined_lut_autocontrast_only(self):
        """
        Test that _build_combined_lut acts as autocontrast when contrast_factor is 1.0.
        """
        mock_thumb = MagicMock(spec=Image.Image)
        mock_thumb.width = 10
        mock_thumb.height = 10

        # Mock histogram:
        # 0-50: 0
        # 100: 50 pixels
        # 200: 50 pixels
        hist = [0] * 256
        hist[100] = 50
        hist[200] = 50

        mock_thumb.histogram.return_value = hist

        # Cutoff = 2% (2 pixels)
        # Low should be 100. High should be 200.
        # Scale = 255 / (100) = 2.55
        # Offset = -255

        # With factor=1.0, it should be pure autocontrast.
        lut = _build_combined_lut(mock_thumb, cutoff=2, contrast_factor=1.0)

        self.assertEqual(len(lut), 256)

        # Value 100 -> 0
        self.assertEqual(lut[100], 0)
        # Value 200 -> 255
        self.assertEqual(lut[200], 255)

        # Value 150 -> 127/128
        # 150 * 2.55 - 255 = 127.5
        self.assertTrue(127 <= lut[150] <= 128)

    def test_combined_lut_flat_image(self):
        """
        Test that _build_combined_lut handles flat histograms.
        """
        mock_thumb = MagicMock(spec=Image.Image)
        mock_thumb.width = 10
        mock_thumb.height = 10

        # All pixels at 128
        hist = [0] * 256
        hist[128] = 100
        mock_thumb.histogram.return_value = hist

        # Low = 128, High = 128. Scale = 1.0, Offset = 0.0.
        # Mean should be 128.
        # Autocontrast is identity.
        # Contrast factor 1.5 -> val = 128 + 1.5 * (val - 128)

        lut = _build_combined_lut(mock_thumb, cutoff=2, contrast_factor=1.5)

        # At 128, result should be 128
        self.assertEqual(lut[128], 128)

        # At 100:
        # ac_val = 100
        # final = 128 + 1.5 * (100 - 128) = 128 + 1.5 * (-28) = 128 - 42 = 86
        self.assertEqual(lut[100], 86)

    def test_combined_lut_contrast_enhance(self):
        """
        Test that contrast factor affects the output.
        """
        mock_thumb = MagicMock(spec=Image.Image)
        mock_thumb.width = 10
        mock_thumb.height = 10

        # Uniform distribution (approx)
        hist = [1] * 256 # total 256 pixels?
        mock_thumb.width = 16
        mock_thumb.height = 16

        mock_thumb.histogram.return_value = hist # fake hist but okay

        # Low ~ 2, High ~ 253 (approx full range)
        # Scale ~ 1.0

        lut_normal = _build_combined_lut(mock_thumb, cutoff=0, contrast_factor=1.0)
        lut_high = _build_combined_lut(mock_thumb, cutoff=0, contrast_factor=2.0)

        # At middle (128), both should be close to 128
        self.assertTrue(abs(lut_normal[128] - 128) < 2)
        self.assertTrue(abs(lut_high[128] - 128) < 2)

        # At dark (50):
        # Normal (factor 1): 50
        # High (factor 2): 128 + 2 * (50 - 128) = 128 - 156 = -28 -> 0
        self.assertTrue(lut_high[50] < lut_normal[50])

if __name__ == "__main__":
    unittest.main()
