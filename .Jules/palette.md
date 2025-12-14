## 2024-05-23 - Chat Action Feedback
**Learning:** Telegram bots often perform long-running tasks (OCR, Chart generation) without visual feedback other than static text. Using `send_chat_action` (typing/upload_photo) provides native, subtle feedback that feels more responsive.
**Action:** Always add `send_chat_action` for operations taking > 1s, matching the action type to the expected output (photo vs text).
