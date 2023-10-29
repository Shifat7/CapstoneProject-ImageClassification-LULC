import sys
import os
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QSizePolicy, QFileDialog,
                             QFrame,QProgressBar, QListWidget, QLabel, QSpacerItem)
from PyQt5.QtGui import QPalette, QColor, QPainter, QBrush, QPixmap
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSlot, QObject
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from visualisation_ourdata import SegmentationThread 
from pie_chart_gui import PieChartDemo
from searcher import get_patches_within_bbox


class DesktopUI(QMainWindow):
    def __init__(self):
        print("list object created")  
        super().__init__()
        self.patch_folder = 'input'
        self.selected_patch_names = []
        self.selected_model_path = []
        self.matching_files = []
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
        
        self.choose_model_btn = QPushButton("Choose Model File (.pth)")
        self.choose_model_btn.setStyleSheet("background-color: transparent; color: white; font-size: 14px;")
        self.choose_model_btn.clicked.connect(self.open_model_dialog)
        col1_layout.addWidget(self.choose_model_btn, alignment=Qt.AlignCenter)

        self.model_path_label = QLabel()
        self.model_path_label.setStyleSheet("color: white; font-size: 8px;")
        self.model_path_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)

        self.clear_model_btn = QPushButton("X")
        self.clear_model_btn.setStyleSheet("background-color: transparent; color: grey; font-size: 8px; max-width: 20px;")
        self.clear_model_btn.clicked.connect(self.clear_model_selection)

        
        model_path_layout = QHBoxLayout()
        model_path_layout.addWidget(self.model_path_label)
        model_path_layout.addWidget(self.clear_model_btn)

        self.clear_model_btn.hide()
        col1_layout.addWidget(self.choose_model_btn)
        col1_layout.addLayout(model_path_layout)
        
        list_patches_btn = QPushButton("List Current Patches")
        list_patches_btn.setStyleSheet("background-color: transparent; color: white; font-size: 14px;")
        list_patches_btn.clicked.connect(self.display_patches_list)
        col1_layout.addWidget(list_patches_btn, alignment=Qt.AlignCenter)
        col1_layout.addSpacing(25)
        
        file_btn = QPushButton("Select Patches")
        file_btn.setStyleSheet("background-color: transparent; color: white; font-size: 14px;")
        file_btn.clicked.connect(self.open_map_dialog)
        col1_layout.addWidget(file_btn, alignment=Qt.AlignCenter)
        
        col1_layout.setSpacing(0)

        col1_frame = QFrame()
        col1_frame.resize(180, 525)
        col1_frame.setLayout(col1_layout)
        col1_frame.setAutoFillBackground(True)

        image_path = "image.png"  
        stylesheet = f"""
            QFrame {{
                border-radius: 10px;
                background-image: url({image_path});
                background-repeat: no-repeat;
                background-position: center;
            }}
        """
        col1_frame.setStyleSheet(stylesheet)

        self.main_layout.addWidget(col1_frame)

        # Column 2
        col2_layout = QVBoxLayout()

        
        square1_layout = QVBoxLayout()

        self.select_all_button = QPushButton('Select All', self)
        self.select_all_button.clicked.connect(self.select_all_patches)
        top_layout = QHBoxLayout()
        spacer_item = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        top_layout.addItem(spacer_item)  
        top_layout.addWidget(self.select_all_button)

        

        square1_layout.addLayout(top_layout)

        
        self.list_widget = QListWidget(self)
        self.list_widget.addItems(self.matching_files)
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        square1_layout.addWidget(self.list_widget)

        # Control buttons 
        control_layout = QHBoxLayout()
        btn_style = "font-size: 10px; width: 7px; height: 10px;"

        
        segment_btn = QPushButton('Start Segmentation', self)
        segment_btn.clicked.connect(self.segment_patches)
        segment_btn.setFixedSize(150, 35)
        control_layout.addWidget(segment_btn, alignment=Qt.AlignLeft)

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

        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                border-radius: 3px;
                text-align: center;
            }

            QProgressBar::chunk {
                background-color: #8EB89E;
                width: 10px;
            }
        """)
        self.progress_animation = QPropertyAnimation(self.progress_bar, b"value")
        self.progress_animation.setEasingCurve(QEasingCurve.OutCubic) 
        square1_layout.addWidget(self.progress_bar)

        # self.progress_details_label = QLabel(self)
        # square1_layout.addWidget(self.progress_details_label)

        
        square1 = RoundedSquare("white")
        square1.setLayout(square1_layout)
        square1.resize(550, 515)
        col2_layout.addWidget(square1)

        col2_frame = QFrame()
        col2_frame.setLayout(col2_layout)
        self.main_layout.addWidget(col2_frame)

        central_widget = QWidget()
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)


    def display_patches_list(self):
        print("Display patches function called")  
        self.list_widget.clear()
        # self.list_widget = QListWidget(self)
        patch_names = [file for file in os.listdir(self.patch_folder) if file.endswith('.tif')]
        self.list_widget.addItems(patch_names)
    
    def select_all_patches(self):
        self.list_widget.selectAll()
    
    def open_model_dialog(self, max_length=30):
        options = QFileDialog.Options()
        model_file_path, _ = QFileDialog.getOpenFileName(self, "Select Model File", "", "Model Files (*.pth);;All Files (*)", options=options)
        if model_file_path:
            self.selected_model_path = model_file_path
            file_name = self.selected_model_path.split('/')[-1]
            
            
            if len(file_name) > max_length:
                file_name = "..." + file_name[-(max_length-20):]
            
            self.model_path_label.setText(file_name)
            self.model_path_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            self.clear_model_btn.show()
        print(f"Model File Chosen: {model_file_path}")
    
    def clear_model_selection(self):
        self.selected_model_path = ""
        self.model_path_label.setText("")
        self.model_path_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        self.clear_model_btn.hide()
        print("Model selection cleared")

    def segment_patches(self):
        print("Segmentation function called")  
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            print("No patch selected!")
            return

        self.selected_patch_names = [item.text() for item in selected_items]
        # self.segmentation_thread = SegmentationThread(self.selected_patch_names)
        self.segmentation_thread = SegmentationThread(self.selected_model_path, self.selected_patch_names)
        self.segmentation_thread.updatePieChartSignal.connect(self.update_pie_chart)
        self.segmentation_thread.progressSignal.connect(self.update_progress)
        self.segmentation_thread.finishedSignal.connect(self.on_segmentation_finished)
        self.segmentation_thread.errorSignal.connect(self.on_segmentation_error)
        self.segmentation_thread.start()

    def update_progress(self, value):
        print(f"Number of patches selected: {self.selected_patch_names}")
        if not hasattr(self, 'selected_patch_names'):
            return

        self.progress_animation.stop()  
        self.progress_animation.setStartValue(self.progress_bar.value())
        self.progress_animation.setEndValue(value)
        self.progress_animation.setDuration(1000) 
        self.progress_animation.start()

        # completed_patches = int(value / 100 * len(self.selected_patch_names))
        # self.progress_details_label.setText(f"{completed_patches}/{len(self.selected_patch_names)} patches processed")

        
        self.segmentation_thread.resetProgressSignal.connect(self.reset_progress_bar)

    def reset_progress_bar(self):
        if hasattr(self, 'progress_animation'):
            self.progress_animation.stop()

        
        self.progress_bar.setValue(0)
        # self.progress_details_label.setText(f"0/{len(self.selected_patch_names)} patches processed")

    
    def update_pie_chart(self, all_output_arrays):
        output_arrays = np.concatenate(all_output_arrays, axis=0)
        
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
        
        if hasattr(self, 'pie_chart_gui') and self.pie_chart_gui is not None:
            self.pie_chart_gui.update_data(data) 
        else:
            self.pie_chart_gui = PieChartDemo(data)
            self.main_layout.addWidget(self.pie_chart_gui)
            return

        self.update()
        self.resize(1200, 500)

    
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
            self.pie_chart_gui.update_data(data) 
        else:
            self.pie_chart_gui = PieChartDemo(data)
            self.main_layout.addWidget(self.pie_chart_gui)

        self.update()
        self.resize(1200, 500)


    
    def on_segmentation_finished(self):
        print("segmentation is running successfully")
        self.display_pie_chart()

    # Slot to handle the signal on segmentation error
    def on_segmentation_error(self, error_message):
        print(f"Error: {error_message}")

    # def remove_pie_chart(self):
    #     if hasattr(self, 'pie_chart_gui'):
    #         self.pie_chart_gui.setParent(None)
    #         self.pie_chart_gui.deleteLater()
    #         self.pie_chart_gui = None


    def start_segmentation(self):
        if hasattr(self, 'segmentation_thread') and self.segmentation_thread.isRunning():
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
            # self.pie_chart_gui.setParent(None)
            # self.pie_chart_gui.deleteLater()

       

    def open_map_dialog(self):
        self.map_window = QMainWindow(self)
        self.map_window.setWindowTitle("Select Location on Map")
        self.map_window.setGeometry(100, 100, 800, 600)

        
        browser = QWebEngineView(self.map_window)
        
        channel = QWebChannel(browser.page())
        browser.page().setWebChannel(channel)

        self.map_handler = MapHandler(self.list_widget)
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
    def __init__(self, list_widget):
        super().__init__()
        self.list_widget = list_widget

    @pyqtSlot('QVariant')
    def receiveMapSelection(self, coords):
        ne_corner = (coords['northEast']['lng'], coords['northEast']['lat'])
        sw_corner = (coords['southWest']['lng'], coords['southWest']['lat'])
        print(f"Selected area NorthEast: {coords['northEast']}, SouthWest: {coords['southWest']}")
        matching_files = get_patches_within_bbox(ne_corner, sw_corner)
        
        # Clear the current items in the list widget
        self.list_widget.clear()

        # Add the matching files to the list widget
        self.list_widget.addItems(matching_files)
        self.list_widget.update()


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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DesktopUI()
    window.show()
    sys.exit(app.exec_())
