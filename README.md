# Ava — Persian Android Assistant

Ava is a Persian-language Android assistant. The pure command parser is isolated from Android APIs so it can be unit-tested on desktop CI.

## Current implemented scope
- Persian command normalization, including Persian and Arabic digits.
- Search web, open validated HTTPS website URLs, navigate-back response, and device lock when Device Admin has been explicitly enabled.
- One-shot Persian speech recognition through Android's system recognizer.
- Voice calls are parsed but are not placed automatically in this baseline; explicit user confirmation and contact resolution must be implemented and tested before enabling.

## Android limitations
- Android restricts background microphone use and background activity launches. This source version does not claim guaranteed always-on wake-word detection.
- Locking requires the user to activate Ava as a Device Administrator in Android settings.
- Call answering and continuous background listening vary by Android version, device manufacturer, roles, and runtime permissions.

## Tests
GitHub Actions runs Python compilation, command-parser unit tests, and Android XML validation. These checks do not replace a build or tests on a physical Android phone.

## Build
APK generation is intentionally not part of the source-test workflow. Build only after source checks pass and Android-specific validation is ready.
