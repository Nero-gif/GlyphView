# GlyphView

GlyphView is a lightweight, modern desktop image viewer for Linux with a built-in "Live Text" (OCR) feature. It seamlessly analyzes text inside your images using Tesseract OCR, allowing you to highlight and copy text directly from the image, just like you would in a standard text document or Google Lens.

## Features

- **Live Text Extraction:** Automatically runs OCR on opened images in the background.
- **Seamless Text Selection:** Click and drag your mouse across the image to linearly select blocks of text in natural reading order.
- **Smart Formatting:** Preserves line breaks when copying text (`Ctrl + C`).
- **Interactive Image Viewer:** 
  - Zoom in and out using `Ctrl + Mouse Wheel`.
  - Pan the image using the `Middle Mouse Button`.
- **Folder Navigation:** Quickly jump to the `Next` or `Previous` image in the current folder using toolbar buttons or the `Left` and `Right` arrow keys.
- **File Manager Integration:** Supports "Open With" integration to open images directly from your OS file manager.

## Installation

The easiest way to install GlyphView on Debian-based distributions (like Linux Mint or Ubuntu) is by using the standalone `.deb` package. The package automatically handles system dependencies (like the Tesseract OCR engine) and sets up desktop integration for your file manager.

1. Download the latest `.deb` package from the [Releases](https://github.com/Nero-gif/GlyphView/releases) page.
2. Install the package using your preferred package manager (e.g., simply double-click the file).

## Usage

Once installed, launch **GlyphView** from your desktop environment's application menu, or right-click an image in your file manager and select "Open With".

**Controls:**
- **Open Image:** Click the button in the top toolbar.
- **Next / Previous Image:** `Left` / `Right` arrow keys.
- **Zoom:** `Ctrl + Mouse Wheel`.
- **Pan (Move):** Click and drag with the `Middle Mouse Button`.
- **Select Text:** Click and drag with the `Left Mouse Button` over the text in the image.
- **Copy Text:** `Ctrl + C`.

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License** (CC BY-NC-SA 4.0). 
See the [LICENSE.md](LICENSE.md) file for more details.

Copyright (c) 2026 Nero ([@Nero-gif](https://github.com/Nero-gif))
