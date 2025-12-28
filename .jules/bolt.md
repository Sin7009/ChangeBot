## 2024-05-23 - [OCR Performance - Resize Method]
**Learning:** `Image.Resampling.LANCZOS` is significantly slower (2-3x) than `BICUBIC` or `BILINEAR`. For OCR preprocessing where we upscale small images, the extreme sharpness of Lanczos is overkill and its computational cost is high.
**Action:** Use `BICUBIC` for image upscaling in performance-critical paths unless the highest possible quality is strictly required. Measure performance with a script before optimizing.

## 2024-05-24 - [Matplotlib Caching - Byte Storage]
**Learning:** When caching objects like `io.BytesIO` that are stateful (have a cursor position), simply caching the object itself leads to bugs where subsequent reads return empty data because the cursor is at the end.
**Action:** Cache the immutable raw data (`bytes` or `buf.getvalue()`) instead of the stateful stream object. Construct a new `io.BytesIO(cached_bytes)` for each consumer. This ensures thread safety and correct behavior for multiple concurrent reads.
