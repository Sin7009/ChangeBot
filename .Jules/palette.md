## 2024-05-23 - Chat Action Feedback
**Learning:** Telegram bots often perform long-running tasks (OCR, Chart generation) without visual feedback other than static text. Using `send_chat_action` (typing/upload_photo) provides native, subtle feedback that feels more responsive.
**Action:** Always add `send_chat_action` for operations taking > 1s, matching the action type to the expected output (photo vs text).

## 2024-05-24 - Error Message Context
**Learning:** Generic error messages like "Not found" in AI/OCR contexts confuse users who don't know the underlying constraints (e.g., strict mode requiring symbols).
**Action:** When rejecting input due to a specific constraint, explicitly state the constraint in the error message with a "💡 Tip" or "Advice" to guide the user to success.

## 2024-05-25 - Onboarding Actionability
**Learning:** The `/start` command often lists text commands which users must type manually. Adding an Inline Keyboard with direct actions (e.g., "Settings", "Try Inline") immediately lowers the friction to engagement and teaches features by doing.
**Action:** Enhance welcome messages with interactive buttons for the most common or "hero" features to encourage immediate exploration.

## 2024-05-26 - Command Argument Friction
**Learning:** Commands requiring arguments (e.g., `/chart <currency>`) often result in "usage error" friction when users forget the syntax or valid options. Presenting a "Quick Pick" menu of popular options when arguments are missing converts a dead-end error into a helpful interaction.
**Action:** For commands with finite or popular argument sets, default to an interactive selection menu instead of a text-only usage error when arguments are omitted.
