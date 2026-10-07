#!/bin/bash
echo "Instaluji systémové závislosti pro GlyphView (Tesseract OCR s češtinou)..."
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-ces

echo ""
echo "Instalace dokončena. Nyní můžete nainstalovat Python závislosti pomocí:"
echo "pip install -r requirements.txt"
