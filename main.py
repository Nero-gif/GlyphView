import sys
import os
import pytesseract
import subprocess
import csv
import io
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QGraphicsPixmapItem, QToolBar, QFileDialog, 
                             QStatusBar, QMessageBox, QGraphicsRectItem)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QKeySequence, QPen, QAction
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class OcrWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.is_cancelled = False
        self._process = None

    def cancel(self):
        """Cancels the running Tesseract process at the OS level."""
        self.is_cancelled = True
        if self._process:
            try:
                self._process.kill()
            except Exception:
                pass

    def run(self):
        if self.is_cancelled:
            return
            
        try:
            cmd = ['tesseract', self.image_path, 'stdout', '-l', 'ces+eng', '--psm', '11', 'tsv']
            
            # Instead of using the pytesseract library, we call Tesseract directly via subprocess.
            # This gives us the ability to instantly kill the process (self._process) at any time.
            self._process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                encoding='utf-8'
            )
            
            # The thread blocks here until the process finishes or is killed
            stdout_data, stderr_data = self._process.communicate()
            
            # If the thread was cancelled during processing, exit immediately
            if self.is_cancelled:
                return

            # Return code -9 usually means SIGKILL (process was killed by us)
            if self._process.returncode != 0 and self._process.returncode != -9:
                self.error.emit(f"Tesseract error:\n{stderr_data}")
                return
                
            data = {'level': [], 'left': [], 'top': [], 'width': [], 'height': [], 'text': []}
            reader = csv.DictReader(io.StringIO(stdout_data), delimiter='\t', quoting=csv.QUOTE_NONE)
            
            for row in reader:
                data['level'].append(int(row.get('level', 0)))
                data['left'].append(int(row.get('left', 0)))
                data['top'].append(int(row.get('top', 0)))
                data['width'].append(int(row.get('width', 0)))
                data['height'].append(int(row.get('height', 0)))
                data['text'].append(row.get('text', ''))
                
            self.finished.emit(data)

        except Exception as e:
            if not self.is_cancelled:
                self.error.emit(str(e))

class OcrTextItem(QGraphicsRectItem):
    """Visual block representing a single detected word."""
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
            self.update() # Forces a repaint

    def paint(self, painter, option, widget=None):
        # Draws a semi-transparent blue rectangle if the text is selected
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
        
        # Variables for linear text selection (mouse dragging)
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
        """Finds the closest word to the cursor position (distance from bounding box)."""
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
            # Start panning the image
            self._is_panning = True
            self._pan_start_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            # Start text selection
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
            # Dragging to select multiple words
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
        """Highlights all words between the start and end indices."""
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
        # Ignore arrow keys so the application can process them as shortcuts for image navigation
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            event.ignore()
            return
            
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selected_text()
        else:
            super().keyPressEvent(event)

    def copy_selected_text(self):
        """Copies the selected text to the clipboard, respecting line breaks."""
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
                # Add a newline if the next word is significantly lower
                if nxt.y() - curr.y() > curr.boundingRect().height() * 0.5:
                    text_parts.append('\n')
                else:
                    text_parts.append(' ')
                    
        full_text = "".join(text_parts)
        QApplication.clipboard().setText(full_text)
        self.textCopied.emit(f"Copied to clipboard.")

class GlyphViewApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GlyphView")
        self.resize(1024, 768)
        
        # State variables for folder navigation
        self.current_folder = ""
        self.image_files = []
        self.current_image_index = -1

        self.scene = QGraphicsScene(self)
        self.view = InteractiveGraphicsView(self.scene, self)
        self.view.textCopied.connect(lambda msg: self.status_bar.showMessage(msg, 4000))
        self.setCentralWidget(self.view)

        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)

        open_action = self.toolbar.addAction("Open Image")
        open_action.triggered.connect(self.open_image)
        
        self.toolbar.addSeparator()
        
        self.prev_action = QAction("Previous", self)
        self.prev_action.triggered.connect(self.prev_image)
        self.prev_action.setShortcut(QKeySequence(Qt.Key.Key_Left))
        self.toolbar.addAction(self.prev_action)
        
        self.next_action = QAction("Next", self)
        self.next_action.triggered.connect(self.next_image)
        self.next_action.setShortcut(QKeySequence(Qt.Key.Key_Right))
        self.toolbar.addAction(self.next_action)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready.")

        self.current_pixmap_item = None
        self.ocr_worker = None

        self.update_nav_buttons()
        self.check_tesseract()

    def update_image_list(self):
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.xpm', '.webp')
        try:
            files = os.listdir(self.current_folder)
            # Filter for images only
            self.image_files = sorted([f for f in files if f.lower().endswith(valid_extensions)])
        except Exception:
            self.image_files = []

    def update_nav_buttons(self):
        has_images = len(self.image_files) > 1
        has_prev = has_images and self.current_image_index > 0
        has_next = has_images and self.current_image_index < len(self.image_files) - 1
        
        self.prev_action.setEnabled(has_prev)
        self.next_action.setEnabled(has_next)

    def prev_image(self):
        if self.current_image_index > 0:
            self.load_image(os.path.join(self.current_folder, self.image_files[self.current_image_index - 1]))

    def next_image(self):
        if self.current_image_index < len(self.image_files) - 1:
            self.load_image(os.path.join(self.current_folder, self.image_files[self.current_image_index + 1]))

    def check_tesseract(self):
        try:
            pytesseract.get_tesseract_version()
        except pytesseract.TesseractNotFoundError:
            QMessageBox.critical(self, "Tesseract not found", 
                                 "Tesseract OCR is not installed or missing from PATH.\n\n"
                                 "In Linux Mint / Ubuntu, you can install it using:\n"
                                 "sudo apt update\n"
                                 "sudo apt install tesseract-ocr tesseract-ocr-ces")
        except Exception as e:
            print(f"Warning during Tesseract detection: {e}")

    def open_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.xpm *.jpg *.jpeg *.bmp *.webp)")
        if file_name:
            self.load_image(file_name)

    def load_image(self, file_path):
        # 1. Immediately cancel the previously running OCR process
        if self.ocr_worker and self.ocr_worker.isRunning():
            self.ocr_worker.cancel()
            self.ocr_worker.wait() # The thread will terminate almost instantly because the process is killed by the OS via SIGKILL
            
        self.scene.clear()
        self.view.set_ocr_items([])
        
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.status_bar.showMessage("Failed to load image.")
            return

        folder = os.path.dirname(os.path.abspath(file_path))
        if folder != self.current_folder:
            self.current_folder = folder
            self.update_image_list()
        
        filename = os.path.basename(file_path)
        if filename in self.image_files:
            self.current_image_index = self.image_files.index(filename)
        self.update_nav_buttons()
        self.setWindowTitle(f"GlyphView - {filename}")

        self.current_pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.current_pixmap_item)
        self.scene.setSceneRect(self.current_pixmap_item.boundingRect())
        
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.status_bar.showMessage("GlyphView is analyzing text...")

        # 2. Start a clean new OCR thread for the current image
        self.ocr_worker = OcrWorker(file_path, parent=self)
        self.ocr_worker.finished.connect(self.on_ocr_finished)
        self.ocr_worker.error.connect(self.on_ocr_error)
        self.ocr_worker.start()

    def on_ocr_finished(self, data):
        if self.sender() != self.ocr_worker:
            return
            
        self.status_bar.showMessage("Analysis complete. You can now drag your mouse to select text and copy it (Ctrl+C).", 7000)
        
        n_boxes = len(data['level'])
        items_list = []
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            if text:
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]

                text_item = OcrTextItem(text, x, y, w, h, len(items_list))
                self.scene.addItem(text_item)
                items_list.append(text_item)
                
        self.view.set_ocr_items(items_list)

    def on_ocr_error(self, err_msg):
        if self.sender() != self.ocr_worker:
            return
        self.status_bar.showMessage("Error analyzing text.")
        QMessageBox.warning(self, "OCR Error", f"An error occurred during OCR analysis:\n{err_msg}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GlyphViewApp()
    window.show()
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.isfile(file_path):
            window.load_image(file_path)
            
    sys.exit(app.exec())
