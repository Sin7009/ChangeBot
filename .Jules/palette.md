## 2024-05-23 - Chat Action Feedback
**Learning:** Telegram bots often perform long-running tasks (OCR, Chart generation) without visual feedback other than static text. Using `send_chat_action` (typing/upload_photo) provides native, subtle feedback that feels more responsive.
**Action:** Always add `send_chat_action` for operations taking > 1s, matching the action type to the expected output (photo vs text).

## 2024-05-24 - Error Message Context
**Learning:** Generic error messages like "Not found" in AI/OCR contexts confuse users who don't know the underlying constraints (e.g., strict mode requiring symbols).
**Action:** When rejecting input due to a specific constraint, explicitly state the constraint in the error message with a "💡 Tip" or "Advice" to guide the user to success.

## 2024-05-25 - Onboarding Actionability
**Learning:** The `/start` command often lists text commands which users must type manually. Adding an Inline Keyboard with direct actions (e.g., "Settings", "Try Inline") immediately lowers the friction to engagement and teaches features by doing.
**Action:** Enhance welcome messages with interactive buttons for the most common or "hero" features to encourage immediate exploration.

## 2024-06-17 - Command Argument Quick-Picks
**Learning:** Commands that strictly require arguments (e.g., `/chart <CODE>`) create a dead end when users forget the argument. Showing a static error message forces them to retype. Presenting a "Quick Pick" keyboard with common options turns an error state into a discovery moment.
**Action:** When a command is invoked without required arguments, default to showing an interactive menu of popular/likely options instead of just an error message.
