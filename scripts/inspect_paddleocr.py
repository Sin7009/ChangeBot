import numpy as np
from PIL import Image, ImageDraw
from paddleocr import PaddleOCR

# Load a test image with text
img = Image.new('RGB', (300, 100), color=(255, 255, 255))
d = ImageDraw.Draw(img)
d.text((20, 20), "100 USD", fill=(0, 0, 0))
img_np = np.array(img)

ocr = PaddleOCR(use_textline_orientation=True, lang="ru", device="gpu")
res = ocr.predict(img_np)
print("Keys of res[0]:", res[0].keys())
# Let's inspect fields
for k, v in res[0].items():
    if k not in ['input_img', 'output_img', 'doc_preprocessor_res']:
        print(f"  {k}: {type(v)} - {str(v)[:300]}")
