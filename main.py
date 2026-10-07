import sys
import os
import pytesseract
from PIL import Image
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QGraphicsPixmapItem, QToolBar, QFileDialog, 
                             QStatusBar, QMessageBox, QGraphicsRectItem)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QKeySequence, QPen
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class OcrWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path

    def run(self):
        try:
            # Získáme data o slovech a jejich pozicích
            # Použijeme mód --psm 11 (Sparse text), který se snaží najít text kdekoli v obrázku bez ohledu na strukturu stránky
            custom_config = r'--psm 11'
            data = pytesseract.image_to_data(Image.open(self.image_path), lang='ces+eng', config=custom_config, output_type=pytesseract.Output.DICT)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

class OcrTextItem(QGraphicsRectItem):
    """Vizuální blok zastupující jedno detekované slovo."""
    def __init__(self, text, x, y, w, h, index):
        super().__init__(0, 0, w, h)
        self.text = text
        self.index = index
        self.setPos(x, y)
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.is_highlighted = False

    def set_highlighted(self, val):
        if self.is_highlighted != val:
            self.is_highlighted = val
            self.update() # Vynutí překreslení

    def paint(self, painter, option, widget=None):
        # Vykreslí poloprůhledný modrý obdélník, pokud je text vybrán (jako klasický výběr textu)
        if self.is_highlighted:
            painter.setBrush(QColor(0, 120, 215, 100)) 
            painter.drawRect(self.boundingRect())

class InteractiveGraphicsView(QGraphicsView):
    textCopied = pyqtSignal(str)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        
        self._is_panning = False
        self._pan_start_pos = None
        
        # Proměnné pro lineární výběr textu (tažením myši)
        self._is_selecting = False
        self._selection_start_index = -1
        self._selection_end_index = -1
        self.ocr_items = []

    def set_ocr_items(self, items):
        self.ocr_items = items
        self.clear_selection()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor
            old_pos = self.mapToScene(event.position().toPoint())
            
            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor
                
            self.scale(zoom_factor, zoom_factor)
            new_pos = self.mapToScene(event.position().toPoint())
            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())
        else:
            super().wheelEvent(event)

    def get_closest_item(self, scene_pos, max_dist):
        """Najde nejbližší slovo k pozici kurzoru (vzdálenost od bounding boxu)."""
        closest_item = None
        min_dist_sq = max_dist ** 2
        for item in self.ocr_items:
            rect = item.sceneBoundingRect()
            dx = max(rect.left() - scene_pos.x(), 0.0, scene_pos.x() - rect.right())
            dy = max(rect.top() - scene_pos.y(), 0.0, scene_pos.y() - rect.bottom())
            dist_sq = dx*dx + dy*dy
            
            if dist_sq <= min_dist_sq:
                min_dist_sq = dist_sq
                closest_item = item
        return closest_item

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            # Začátek posouvání obrazu (panning)
            self._is_panning = True
            self._pan_start_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            # Začátek výběru textu
            pos = self.mapToScene(event.position().toPoint())
            closest = self.get_closest_item(pos, max_dist=80)
            if closest:
                self._is_selecting = True
                self._selection_start_index = closest.index
                self._selection_end_index = closest.index
                self.update_selection()
            else:
                self.clear_selection()
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
        elif self._is_selecting:
            # Tažení pro výběr více slov do bloku
            pos = self.mapToScene(event.position().toPoint())
            closest = self.get_closest_item(pos, max_dist=200)
            if closest:
                self._selection_end_index = closest.index
                self.update_selection()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def update_selection(self):
        """Zvýrazní všechna slova mezi počátečním a koncovým indexem."""
        start = min(self._selection_start_index, self._selection_end_index)
        end = max(self._selection_start_index, self._selection_end_index)
        for item in self.ocr_items:
            item.set_highlighted(start <= item.index <= end)

    def clear_selection(self):
        for item in self.ocr_items:
            item.set_highlighted(False)
        self._selection_start_index = -1
        self._selection_end_index = -1

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selected_text()
        else:
            super().keyPressEvent(event)

    def copy_selected_text(self):
        """Zkopíruje vybraný text do schránky s ohledem na řádkování."""
        if not self.ocr_items:
            return
        
        start = min(self._selection_start_index, self._selection_end_index)
        end = max(self._selection_start_index, self._selection_end_index)
        
        if start == -1 or end == -1:
            return
            
        selected_items = [item for item in self.ocr_items if start <= item.index <= end]
        
        text_parts = []
        for i in range(len(selected_items)):
            text_parts.append(selected_items[i].text)
            if i < len(selected_items) - 1:
                curr = selected_items[i]
                nxt = selected_items[i+1]
                # Přidání nového řádku, pokud je další slovo výrazně níže (např. o polovinu výšky aktuálního slova)
                if nxt.y() - curr.y() > curr.boundingRect().height() * 0.5:
                    text_parts.append('\n')
                else:
                    text_parts.append(' ')
                    
        full_text = "".join(text_parts)
        QApplication.clipboard().setText(full_text)
        self.textCopied.emit(f"Zkopírováno do schránky.")

class GlyphViewApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GlyphView")
        self.resize(1024, 768)

        self.scene = QGraphicsScene(self)
        self.view = InteractiveGraphicsView(self.scene, self)
        self.view.textCopied.connect(lambda msg: self.status_bar.showMessage(msg, 4000))
        self.setCentralWidget(self.view)

        self.toolbar = QToolBar("Hlavní panel")
        self.addToolBar(self.toolbar)

        open_action = self.toolbar.addAction("Otevřít obrázek")
        open_action.triggered.connect(self.open_image)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Připraven.")

        self.current_pixmap_item = None
        self.ocr_worker = None

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
        self.view.set_ocr_items([])
        
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.status_bar.showMessage("Nepodařilo se načíst obrázek.")
            return

        self.current_pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.current_pixmap_item)
        self.scene.setSceneRect(self.current_pixmap_item.boundingRect())
        
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        self.status_bar.showMessage("GlyphView analyzuje text...")

        self.ocr_worker = OcrWorker(file_path)
        self.ocr_worker.finished.connect(self.on_ocr_finished)
        self.ocr_worker.error.connect(self.on_ocr_error)
        self.ocr_worker.start()

    def on_ocr_finished(self, data):
        self.status_bar.showMessage("Analýza dokončena. Nyní můžete tažením myši označit text a zkopírovat ho (Ctrl+C).", 7000)
        
        n_boxes = len(data['level'])
        items_list = []
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            if text:
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]

                # Reprezentuje detekované slovo - bez viditelného textu, 
                # ale schopné se "obarvit" při výběru
                text_item = OcrTextItem(text, x, y, w, h, len(items_list))
                self.scene.addItem(text_item)
                items_list.append(text_item)
                
        # Předáme seznam prvků zachovávající pořadí čtení do pohledu
        self.view.set_ocr_items(items_list)

    def on_ocr_error(self, err_msg):
        self.status_bar.showMessage("Chyba při analýze textu.")
        QMessageBox.warning(self, "OCR Chyba", f"Došlo k chybě při OCR analýze:\n{err_msg}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GlyphViewApp()
    window.show()
    sys.exit(app.exec())
