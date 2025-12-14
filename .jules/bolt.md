## 2024-05-23 - [OCR Performance - Resize Method]
**Learning:** `Image.Resampling.LANCZOS` is significantly slower (2-3x) than `BICUBIC` or `BILINEAR`. For OCR preprocessing where we upscale small images, the extreme sharpness of Lanczos is overkill and its computational cost is high.
**Action:** Use `BICUBIC` for image upscaling in performance-critical paths unless the highest possible quality is strictly required. Measure performance with a script before optimizing.
