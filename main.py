import sys
import os
import pytesseract
from PIL import Image
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QGraphicsPixmapItem, QGraphicsTextItem, QToolBar, QFileDialog, 
                             QStatusBar, QMessageBox)
from PyQt6.QtGui import QPixmap, QFont, QPainter
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class OcrWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path

    def run(self):
        try:
            # Spuštění Tesseract OCR na pozadí, vyžaduje češtinu a angličtinu
            data = pytesseract.image_to_data(Image.open(self.image_path), lang='ces+eng', output_type=pytesseract.Output.DICT)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

class InteractiveGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        # Optimalizace pro vykreslování
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        
        # Povolíme Drag mód bez gumového výběru (aby neinterferoval s výběrem textu)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        
        self._is_panning = False
        self._pan_start_pos = None

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Zoomování pomocí Ctrl + Kolečko
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor
            
            # Uložíme si původní pozici pod kurzorem
            old_pos = self.mapToScene(event.position().toPoint())
            
            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor
                
            self.scale(zoom_factor, zoom_factor)
            
            # Najdeme novou pozici pod kurzorem
            new_pos = self.mapToScene(event.position().toPoint())
            
            # Posuneme scénu tak, aby kurzor zůstal na stejném místě obrázku
            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())
        else:
            # Standardní scrollování (bez Ctrl)
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        # Panning pomocí prostředního tlačítka myši
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._pan_start_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = event.position().toPoint() - self._pan_start_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._pan_start_pos = event.position().toPoint()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class GlyphViewApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GlyphView")
        self.resize(1024, 768)

        # Hlavní plocha pro zobrazení
        self.scene = QGraphicsScene(self)
        self.view = InteractiveGraphicsView(self.scene, self)
        self.setCentralWidget(self.view)

        # Panel nástrojů
        self.toolbar = QToolBar("Hlavní panel")
        self.addToolBar(self.toolbar)

        open_action = self.toolbar.addAction("Otevřít obrázek")
        open_action.triggered.connect(self.open_image)

        # Stavový řádek
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Připraven.")

        self.current_pixmap_item = None
        self.ocr_worker = None

        # Ověření, že Tesseract je dostupný
        self.check_tesseract()

    def check_tesseract(self):
        try:
            pytesseract.get_tesseract_version()
        except pytesseract.TesseractNotFoundError:
            QMessageBox.critical(self, "Tesseract nenalezen", 
                                 "Tesseract OCR není v systému nainstalován nebo chybí v PATH.\n\n"
                                 "V Linux Mint / Ubuntu ho můžete nainstalovat pomocí:\n"
                                 "sudo apt update\n"
                                 "sudo apt install tesseract-ocr tesseract-ocr-ces")
        except Exception as e:
            print(f"Varování při detekci Tesseractu: {e}")

    def open_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Otevřít obrázek", "", "Images (*.png *.xpm *.jpg *.jpeg *.bmp)")
        if file_name:
            self.load_image(file_name)

    def load_image(self, file_path):
        self.scene.clear()
        
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.status_bar.showMessage("Nepodařilo se načíst obrázek.")
            return

        # Přidání obrázku do scény
        self.current_pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.current_pixmap_item)
        self.scene.setSceneRect(self.current_pixmap_item.boundingRect())
        
        # Přizpůsobení zobrazení (vejde se do okna)
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        self.status_bar.showMessage("GlyphView analyzuje text...")

        # Asynchronní OCR analýza
        self.ocr_worker = OcrWorker(file_path)
        self.ocr_worker.finished.connect(self.on_ocr_finished)
        self.ocr_worker.error.connect(self.on_ocr_error)
        self.ocr_worker.start()

    def on_ocr_finished(self, data):
        self.status_bar.showMessage("Analýza dokončena. Text je připraven k výběru.", 5000)
        
        n_boxes = len(data['level'])
        for i in range(n_boxes):
            text = data['text'][i].strip()
            if text:
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]

                text_item = QGraphicsTextItem(text)
                
                # Nastavení fontu a výšky podle velikosti detekovaného slova
                font = QFont("sans-serif")
                font.setPixelSize(h)
                text_item.setFont(font)
                
                # Odstranění okrajů, aby text těsně lícoval s boxem
                text_item.document().setDocumentMargin(0)
                
                # Skrytí barvy textu - uživatel vidí původní text v obrázku,
                # ale může vybírat průhledný text přes něj.
                text_item.setDefaultTextColor(Qt.GlobalColor.transparent)
                
                # Umístění na souřadnice z OCR
                text_item.setPos(x, y)
                
                # Povolení výběru textu myší
                text_item.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                
                self.scene.addItem(text_item)

    def on_ocr_error(self, err_msg):
        self.status_bar.showMessage("Chyba při analýze textu.")
        QMessageBox.warning(self, "OCR Chyba", f"Došlo k chybě při OCR analýze:\n{err_msg}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GlyphViewApp()
    window.show()
    sys.exit(app.exec())
