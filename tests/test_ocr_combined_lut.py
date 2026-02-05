import unittest
from PIL import Image
from src.services.ocr import _build_combined_lut

class TestOCRCombinedLUT(unittest.TestCase):
    def test_lut_generation_flat_image(self):
        # Create a flat gray image
        img = Image.new('L', (100, 100), color=100)

        # Build LUT
        lut = _build_combined_lut(img, contrast_factor=1.5, cutoff=0)

        # For a flat image, min=100, max=100.
        # Logic: if high <= low (which is 100 <= 100), scale=1.0, offset=0.0.
        # Mean = 100.
        # Autocontrast: y = x.
        # Contrast: z = (x - 100) * 1.5 + 100.
        # For input 100: z = 0 + 100 = 100.

        self.assertEqual(len(lut), 256)
        self.assertEqual(lut[100], 100)

    def test_lut_generation_gradient(self):
        # Create a gradient image covering full range
        img = Image.linear_gradient('L')
        # Resize to small to be used as thumb
        thumb = img.resize((100, 100))

        lut = _build_combined_lut(thumb, contrast_factor=1.5, cutoff=0)

        self.assertEqual(len(lut), 256)
        # Verify valid values
        for val in lut:
            self.assertIsInstance(val, int)
            self.assertTrue(0 <= val <= 255)

    def test_lut_contrast_effect(self):
        # Case where contrast should stretch values
        # Image with values 100 and 150.
        # Mean approx 125.
        # Autocontrast with cutoff=0 will map 100->0 and 150->255?
        # Let's check logic:
        # scale = 255 / (150 - 100) = 5.1
        # offset = -100 * 5.1 = -510.
        # 100 -> 0.
        # 150 -> 255.
        # Mean 125 -> 127.5 (approx).
        # Contrast around 127.5 does not change 0 and 255 much (clamped).

        # Let's create an image with known range
        data = bytes([100] * 50 + [150] * 50)
        img = Image.frombytes('L', (10, 10), data) # 100 pixels

        lut = _build_combined_lut(img, contrast_factor=1.0, cutoff=0)

        # With factor 1.0, it should be just autocontrast
        # 100 -> 0
        self.assertEqual(lut[100], 0)
        # 150 -> 255
        self.assertEqual(lut[150], 255)

    def test_lut_with_cutoff(self):
         # Image with outliers
        data = bytes([0] * 5 + [100] * 45 + [150] * 45 + [255] * 5)
        img = Image.frombytes('L', (10, 10), data)

        # Cutoff 5 pixels (5%).
        # Low should ignore 0s, start at 100.
        # High should ignore 255s, end at 150.
        # So range 100-150 -> 0-255.

        lut = _build_combined_lut(img, contrast_factor=1.0, cutoff=5)

        self.assertEqual(lut[100], 0)
        self.assertEqual(lut[150], 255)
        # Outliers clamped
        self.assertEqual(lut[0], 0)
        self.assertEqual(lut[255], 255)
