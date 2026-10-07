#!/bin/bash
set -e

VERSION="1.0.0"
DEB_DIR="glyphview_${VERSION}_amd64"

echo "1. Instaluji PyInstaller (nástroj pro kompilaci do jedné binárky)..."
pip install pyinstaller

echo "2. Kompiluji aplikaci přes PyInstaller..."
# --windowed zajistí, že na pozadí nevyskočí terminál
# --onefile vše zabalí do jediného souboru
pyinstaller --onefile --windowed --name glyphview main.py

echo "3. Připravuji finální adresářovou strukturu balíčku..."
rm -rf "$DEB_DIR"
mkdir -p "$DEB_DIR"

# Kopírování šablony s metadaty a desktop souborem
cp -r debian_template/* "$DEB_DIR/"

echo "4. Přesouvám binárku do debian struktury..."
cp dist/glyphview "$DEB_DIR/usr/bin/"
chmod +x "$DEB_DIR/usr/bin/glyphview"

echo "------------------------------------------------------"
echo "✅ Struktura balíčku je připravena ve složce '$DEB_DIR'."
echo "Prozatím jsme žádný .deb nevytvořili."
echo "Až budeš chtít balíček .deb fyzicky vytvořit, spusť příkaz:"
echo "dpkg-deb --build $DEB_DIR"
echo "------------------------------------------------------"
