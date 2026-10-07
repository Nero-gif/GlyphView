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

## Requirements

- **Python 3**
- **System packages:** `tesseract-ocr` (and language packs like `tesseract-ocr-ces` for Czech)
- **Python packages:** `PyQt6`, `pytesseract`, `Pillow`

## Installation

### 1. Install System Dependencies (Linux Mint / Ubuntu / Debian)
You need to install the Tesseract OCR engine and the necessary language packs.
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-ces
```
*(Alternatively, you can run the provided `install_dependencies.sh` script).*

### 2. Install Python Dependencies
It is highly recommended to use a virtual environment.
```bash
pip install -r requirements.txt
```

### 3. (Optional) Build a Debian Package (.deb)
To create a standalone `.deb` package with desktop integration (so you can right-click an image and choose "Open with GlyphView"):
```bash
./prepare_deb.sh
```
The script will compile the app and prepare the Debian structure. It will then output the final command you need to run to build the `.deb` file, which is:
```bash
dpkg-deb --build glyphview_1.0.0_amd64
```
You can install the generated package using `sudo apt install ./glyphview_1.0.0_amd64.deb`.

## Usage

Start the application from the terminal:
```bash
python main.py
```
*Or, if you installed the `.deb` package, launch **GlyphView** from your application menu or right-click an image in your file manager.*

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
