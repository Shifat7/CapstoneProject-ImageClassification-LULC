import sys
import os
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QComboBox, QFileDialog,
                             QFrame, QDateEdit, QCalendarWidget, QLabel, QSizePolicy, QListWidget)
from PyQt5.QtGui import QPalette, QColor, QPainter, QBrush, QPixmap
from PyQt5.QtCore import Qt, QDate, pyqtSlot, QObject
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from visualisation_ourdata import SegmentationThread 
from pie_chart_gui import PieChartDemo

class RoundedSquare(QFrame):
    def __init__(self, color, parent=None):
        super(RoundedSquare, self).__init__(parent)
        self.color = color

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        brush = QBrush(QColor(self.color))
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 10, 10)

class DesktopUI(QMainWindow):
    def __init__(self):
        print("list object created")  
        super().__init__()
        self.patch_folder = 'Patch_Cropper/patches_test'
        self.init_ui()

    def init_ui(self):
        super(DesktopUI, self).__init__()

        # Window setup
        self.setWindowTitle("Desktop UI")
        self.resize(550, 450)

        # Setting the main layout
        self.main_layout = QHBoxLayout()


        # Column 1
        col1_layout = QVBoxLayout()
        col1_layout.setAlignment(Qt.AlignCenter)

        self.model_dropdown = QComboBox()
        self.model_dropdown.setFocusPolicy(Qt.NoFocus)
        self.model_dropdown.setStyleSheet("background-color: transparent; color: white; font-size: 14px;")
        self.model_dropdown.addItem("SwinUnet")
        # self.model_dropdown.addItem("SwinUnet")
        col1_layout.addWidget(self.model_dropdown)

        list_patches_btn = QPushButton("List Current Patches")
        list_patches_btn.setStyleSheet("background-color: transparent; color: white; font-size: 14px;")
        list_patches_btn.clicked.connect(self.display_patches)
        col1_layout.addWidget(list_patches_btn, alignment=Qt.AlignCenter)
        
        file_btn = QPushButton("Select Patches")
        file_btn.setStyleSheet("background-color: transparent; color: white; font-size: 14px;")
        file_btn.clicked.connect(self.open_map_dialog)
        col1_layout.addWidget(file_btn, alignment=Qt.AlignCenter)
        
        col1_layout.setSpacing(20)
        col1_frame = QFrame()
        col1_frame.setLayout(col1_layout)
        col1_frame.setAutoFillBackground(True)
        palette = col1_frame.palette()
        palette.setColor(QPalette.Window, QColor("darkgreen"))
        col1_frame.setPalette(palette)
        self.main_layout.addWidget(col1_frame)

        # Column 2
        col2_layout = QVBoxLayout()

         # Square 1
        square1_layout = QVBoxLayout()
        # square1_layout.setAlignment(Qt.AlignCenter)  
        self.list_widget = QListWidget(self)
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)  
        square1_layout.addWidget(self.list_widget)

        select_all_button = QPushButton('Select All', self)
        select_all_button.clicked.connect(self.select_all_patches)
        square1_layout.addWidget(select_all_button)

        segment_btn = QPushButton('Start Segmentation', self)
        segment_btn.clicked.connect(self.segment_patches)
        square1_layout.addWidget(segment_btn, alignment=Qt.AlignCenter)

        # Control buttons 
        control_layout = QHBoxLayout()
        btn_style = "font-size: 10px; width: 10px; height: 10px;"  
        stop_btn = QPushButton("■")
        stop_btn.setStyleSheet(btn_style)
        stop_btn.clicked.connect(self.stop_segmentation)

        pause_btn = QPushButton("❙❙")
        pause_btn.setStyleSheet(btn_style)
        pause_btn.clicked.connect(self.pause_segmentation)

        play_btn = QPushButton("▶")
        play_btn.setStyleSheet(btn_style)
        play_btn.clicked.connect(self.start_segmentation)
        
        control_layout.addWidget(stop_btn)
        control_layout.addWidget(pause_btn)
        control_layout.addWidget(play_btn)

        square1_layout.addLayout(control_layout)

        square1 = RoundedSquare("white")
        square1.setLayout(square1_layout)
        square1.setFixedSize(324, 400)
        col2_layout.addWidget(square1)

        col2_frame = QFrame()
        col2_frame.setLayout(col2_layout)
        self.main_layout.addWidget(col2_frame)

        # main_layout.setStretch(0, 2)
        # main_layout.setStretch(1, 8)

        central_widget = QWidget()
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)


    def display_patches(self):
        print("Display patches function called")  
        patch_names = [file for file in os.listdir(self.patch_folder) if file.endswith('.tif')]
        self.list_widget.addItems(patch_names)
    
    def select_all_patches(self):
        self.list_widget.selectAll()

    def segment_patches(self):
        print("Segment patches function called")  
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            print("No patch selected!")
            return

        selected_patch_names = [item.text() for item in selected_items]
        self.segmentation_thread = SegmentationThread(selected_patch_names)
        self.segmentation_thread.finishedSignal.connect(self.on_segmentation_finished)
        self.segmentation_thread.errorSignal.connect(self.on_segmentation_error)
        self.segmentation_thread.start()

    def display_pie_chart(self):
        output_arrays = np.load('npy_outputs/all_output_arrays.npy')
        unique_elements, counts_elements = np.unique(output_arrays, return_counts=True)
        total_count = np.sum(counts_elements)
        class_mapping = {
            0: "Forest",
            1: "Shrubland",
            2: "Grassland",
            3: "Wetlands",
            4: "Croplands",
            5: "Urban/Built-up",
            6: "Barren",
            7: "Water",
            255: "Invalid",
        }
        data = {class_mapping[label]: (count / total_count) * 100 for label, count in zip(unique_elements, counts_elements) if label in class_mapping}

        # Initialize the PieChartDemo
        if hasattr(self, 'pie_chart_gui'):
            self.pie_chart_gui.setParent(None)  
            self.pie_chart_gui.deleteLater() 
        
        self.pie_chart_gui = PieChartDemo(data)
        # self.pie_chart_gui.setFixedSize(350, 400)
        self.pie_chart_gui.setStyleSheet("border: none;")

        self.main_layout.addWidget(self.pie_chart_gui)

        self.update()
        self.resize(1200, 500)

    # Slot to handle the signal when segmentation finishes
    def on_segmentation_finished(self):
        self.display_pie_chart()

    # Slot to handle the signal on segmentation error
    def on_segmentation_error(self, error_message):
        print(f"Error: {error_message}")

    # Connect these functions to the respective buttons in your GUI:

    def start_segmentation(self):
    
        if not hasattr(self, 'segmentation_thread') or not self.segmentation_thread.isRunning():
            print("Starting a new thread")
            self.segmentation_thread = SegmentationThread(self.selected_patch_names)
            self.segmentation_thread.start()
        else:
            print("Resuming thread")
            self.segmentation_thread.resume()

    def pause_segmentation(self):
        if hasattr(self, 'segmentation_thread'):
            print("pause button")
            self.segmentation_thread.pause()

    def stop_segmentation(self):
        if hasattr(self, 'segmentation_thread'):
            print("stop button pressed")
            self.segmentation_thread.stop()

    def open_map_dialog(self):
        self.map_window = QMainWindow(self)
        self.map_window.setWindowTitle("Select Location on Map")
        self.map_window.setGeometry(100, 100, 800, 600)
        
        browser = QWebEngineView(self.map_window)
        
        channel = QWebChannel(browser.page())
        browser.page().setWebChannel(channel)

        self.map_handler = MapHandler()
        channel.registerObject('mapHandler', self.map_handler)

        # Load HTML with Leaflet and Leaflet.draw 
        browser.setHtml("""
            <html>
                <head>
                    <title>Interactive Map</title>
                    <meta charset="utf-8" />
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
                    <link rel="stylesheet" href="https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.css" />
                    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
                    <script src="https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.js"></script>
                    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
                </head>
                <body>
                    <div id="map" style="width: 800px; height: 600px;"></div>
                    <script>
                        var map = L.map('map').setView([-37.8136, 144.9631], 10);
                        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

                        var drawnItems = new L.FeatureGroup();
                        map.addLayer(drawnItems);

                        var drawControl = new L.Control.Draw({
                            draw: {
                                polyline: false,
                                polygon: false,
                                circle: false,
                                marker: false,
                                circlemarker: false
                            },
                            edit: {
                                featureGroup: drawnItems
                            }
                        });
                        map.addControl(drawControl);

                        map.on(L.Draw.Event.CREATED, function (e) {
                            var type = e.layerType;
                            var layer = e.layer;

                            if (type === 'rectangle') {
                                var coords = {
                                    northEast: layer.getBounds().getNorthEast(),
                                    southWest: layer.getBounds().getSouthWest()
                                };

                                new QWebChannel(qt.webChannelTransport, function(channel) {
                                    var mapHandler = channel.objects.mapHandler;
                                    mapHandler.receiveMapSelection(coords);
                                });
                            }

                            drawnItems.addLayer(layer);
                        });
                    </script>
                </body>
            </html>
        """)
        
        self.map_window.setCentralWidget(browser)
        self.map_window.show()

class MapHandler(QObject):
    @pyqtSlot('QVariant')
    def receiveMapSelection(self, coords):
        print(f"Selected area NorthEast: {coords['northEast']}, SouthWest: {coords['southWest']}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DesktopUI()
    window.show()
    sys.exit(app.exec_())
