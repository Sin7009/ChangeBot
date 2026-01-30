import unittest
from unittest.mock import MagicMock
from PIL import Image
from src.services.ocr import _get_autocontrast_params, _build_combined_lut

class TestOCRCombinedLUT(unittest.TestCase):
    def test_get_autocontrast_params_stretches_contrast(self):
        """
        Test that _get_autocontrast_params calculates correct scale and offset.
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

        # Cutoff = 2% (2 pixels)
        # Low should be 100. High should be 200.
        # Scale = 255 / (200 - 100) = 2.55
        # Offset = -100 * 2.55 = -255

        params = _get_autocontrast_params(mock_thumb, cutoff=2)

        self.assertIsNotNone(params)
        scale, offset = params

        self.assertAlmostEqual(scale, 2.55)
        self.assertAlmostEqual(offset, -255.0)

    def test_get_autocontrast_params_flat_image(self):
        """
        Test that _get_autocontrast_params returns None if histogram is flat.
        """
        mock_thumb = MagicMock(spec=Image.Image)
        mock_thumb.width = 10
        mock_thumb.height = 10

        # All pixels at 128
        hist = [0] * 256
        hist[128] = 100
        mock_thumb.histogram.return_value = hist

        params = _get_autocontrast_params(mock_thumb, cutoff=2)

        self.assertIsNone(params)

    def test_build_combined_lut_inversion(self):
        """
        Test that LUT handles inversion correctly.
        """
        lut = _build_combined_lut(
            invert=True,
            ac_params=None,
            contrast_factor=1.0,
            contrast_center=128.0
        )

        # 0 -> 255
        self.assertEqual(lut[0], 255)
        # 255 -> 0
        self.assertEqual(lut[255], 0)
        # 128 -> 127 (255 - 128)
        self.assertEqual(lut[128], 127)

    def test_build_combined_lut_autocontrast(self):
        """
        Test that LUT handles autocontrast params correctly.
        """
        # Scale = 2.0, Offset = -100.0
        # 0 -> 0*2 - 100 = -100 -> clamped 0
        # 50 -> 50*2 - 100 = 0 -> 0
        # 100 -> 100*2 - 100 = 100 -> 100
        # 150 -> 150*2 - 100 = 200 -> 200
        # 200 -> 200*2 - 100 = 300 -> clamped 255

        lut = _build_combined_lut(
            invert=False,
            ac_params=(2.0, -100.0),
            contrast_factor=1.0,
            contrast_center=128.0
        )

        self.assertEqual(lut[0], 0)
        self.assertEqual(lut[50], 0)
        self.assertEqual(lut[100], 100)
        self.assertEqual(lut[150], 200)
        self.assertEqual(lut[200], 255)

    def test_build_combined_lut_contrast_enhance(self):
        """
        Test that LUT handles contrast enhancement correctly.
        """
        # Factor = 1.5, Center = 100
        # val = 100 + (val - 100) * 1.5

        # 100 -> 100 + 0 = 100
        # 120 -> 100 + 20*1.5 = 130
        # 80 -> 100 - 20*1.5 = 70

        lut = _build_combined_lut(
            invert=False,
            ac_params=None,
            contrast_factor=1.5,
            contrast_center=100.0
        )

        self.assertEqual(lut[100], 100)
        self.assertEqual(lut[120], 130)
        self.assertEqual(lut[80], 70)

    def test_build_combined_lut_all(self):
        """
        Test combined pipeline: Invert -> Autocontrast -> Enhance
        """
        # Invert: val = 255 - val
        # AC: Scale=2, Offset=0 -> val = val * 2
        # Enhance: Factor=1.5, Center=128 -> val = 128 + (val - 128) * 1.5

        lut = _build_combined_lut(
            invert=True,
            ac_params=(2.0, 0.0),
            contrast_factor=1.5,
            contrast_center=128.0
        )

        # Input 200
        # 1. Invert: 255 - 200 = 55
        # 2. AC: 55 * 2 = 110
        # 3. Enhance: 128 + (110 - 128) * 1.5 = 128 + (-18 * 1.5) = 128 - 27 = 101

        self.assertEqual(lut[200], 101)

if __name__ == "__main__":
    unittest.main()
