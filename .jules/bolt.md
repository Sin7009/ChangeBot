## 2024-05-23 - [OCR Performance - Resize Method]
**Learning:** `Image.Resampling.LANCZOS` is significantly slower (2-3x) than `BICUBIC` or `BILINEAR`. For OCR preprocessing where we upscale small images, the extreme sharpness of Lanczos is overkill and its computational cost is high.
**Action:** Use `BICUBIC` for image upscaling in performance-critical paths unless the highest possible quality is strictly required. Measure performance with a script before optimizing.

## 2024-05-24 - [Matplotlib Caching - Byte Storage]
**Learning:** When caching objects like `io.BytesIO` that are stateful (have a cursor position), simply caching the object itself leads to bugs where subsequent reads return empty data because the cursor is at the end.
**Action:** Cache the immutable raw data (`bytes` or `buf.getvalue()`) instead of the stateful stream object. Construct a new `io.BytesIO(cached_bytes)` for each consumer. This ensures thread safety and correct behavior for multiple concurrent reads.

## 2024-05-25 - [Regex Performance - Trie Optimization]
**Learning:** Python's `re` module does not automatically optimize large disjunctions (e.g. `word1|word2|...|word50`) into a Trie structure. This results in O(N*M) matching complexity where M is the number of alternatives.
**Action:** For matching against a fixed set of keywords (like currency codes), pre-compile the list into a Trie-based regex pattern (e.g. `u(?:sd(?:t)?)?`). This reduces backtracking and improves matching speed by ~30-40%.

## 2024-05-30 - [Regex Performance - Precompilation]
**Learning:** Even simple regex operations like `re.search(r'\d', text)` incur compilation overhead if called repeatedly in a hot loop. Precompiling the regex pattern (`HAS_DIGIT_PATTERN = re.compile(r'\d')`) and using its `search` method reduces this overhead significantly.
**Action:** Precompile all regex patterns at the module or class level, even "simple" ones, if they are used in high-frequency paths like message parsing. Benchmarking showed a ~2.2x - 2.9x speedup for the specific check.

## 2024-06-05 - [String Operations vs Regex]
**Learning:** For simple structural checks like "suffix length", pure string operations (`rsplit`, `len`) are faster (~1.2x) than precompiled regex. Regex incurs overhead even for simple patterns.
**Action:** When validating simple string formats (e.g. "digits,digits"), prefer built-in string methods over regex if possible. Use `timeit` to confirm as the difference can be small in Python.
