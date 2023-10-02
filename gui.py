import sys
import time  # Import the time module
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QComboBox, QFileDialog,
                             QFrame, QDateEdit, QCalendarWidget, QLabel, QDialog,
                             QProgressBar)  # Import QProgressBar
from PyQt5.QtGui import QPalette, QColor, QPainter, QBrush, QPixmap
from PyQt5.QtCore import Qt, QDate, pyqtSlot, QObject
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtChart import QChart, QChartView, QPieSeries

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
        super(DesktopUI, self).__init__()

        # Window setup
        self.setWindowTitle("Desktop UI")
        self.setFixedSize(900, 450)

        # Setting the main layout
        main_layout = QHBoxLayout()

        # Column 1
        col1_layout = QVBoxLayout()
        col1_layout.setAlignment(Qt.AlignCenter)
        show_pie_chart_btn = QPushButton("Show Pie Chart")
        show_pie_chart_btn.setStyleSheet("background-color: transparent; color: white; font-size: 14px;")
        show_pie_chart_btn.clicked.connect(self.show_pie_chart)
        col1_layout.addWidget(show_pie_chart_btn, alignment=Qt.AlignCenter)

        self.model_dropdown = QComboBox()
        self.model_dropdown.setFocusPolicy(Qt.NoFocus)
        self.model_dropdown.setStyleSheet("background-color: transparent; color: white; font-size: 14px;")
        self.model_dropdown.addItem("Select Model")
        self.model_dropdown.addItem("SwinUnet")
        col1_layout.addWidget(self.model_dropdown)
        
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
        main_layout.addWidget(col1_frame)

        # Column 2
        col2_layout = QHBoxLayout()

        # Square 1
        square1_layout = QVBoxLayout()
        square1_layout.setAlignment(Qt.AlignCenter)  # Center align content

        
        self.date_picker = QDateEdit(calendarPopup=True)
        self.date_picker.setCalendarWidget(QCalendarWidget())
        self.date_picker.setDate(QDate.currentDate())
        square1_layout.addWidget(self.date_picker, alignment=Qt.AlignCenter)

        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        square1_layout.addWidget(self.image_label)

        
        segment_btn = QPushButton("Start Segmentation")
        square1_layout.addWidget(segment_btn, alignment=Qt.AlignCenter)

        square1 = RoundedSquare("white")
        square1.setLayout(square1_layout)
        square1.setFixedSize(324, 400)
        col2_layout.addWidget(square1)

        # Square 2
        square2_layout = QVBoxLayout()

        # Control buttons 
        control_layout = QHBoxLayout()
        btn_style = "font-size: 14px; width: 54px;"  
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
        
        square2_layout.addLayout(control_layout)
        square2_layout.addStretch(1)

        square2 = RoundedSquare("white")
        square2.setLayout(square2_layout)
        square2.setFixedSize(324, 400)
        col2_layout.addWidget(square2)
        
        col2_frame = QFrame()
        col2_frame.setLayout(col2_layout)
        main_layout.addWidget(col2_frame)

        # Create a progress bar and add it to the layout
        self.progress_bar = QProgressBar()
        col2_layout.addWidget(self.progress_bar, alignment=Qt.AlignCenter)

        # Set the initial value and properties of the progress bar
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        main_layout.setStretch(0, 2)
        main_layout.setStretch(1, 8)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Connecting buttons to their respective slots
        segment_btn.clicked.connect(self.start_segmentation)
        
    def show_pie_chart(self):
    # Define your class data
        class_data = {
            0: "Forest",
            1: "Shrubland",
            2: "Grassland",
            3: "Wetlands",
            4: "Croplands",
            5: "Urban/Built-up",
            6: "Barren",
            7: "Water",
            255: "Invalid"
        }

        # Sample data for class distribution (you can replace this with your data)
        class_distribution = {
            "Forest": 30,
            "Shrubland": 20,
            "Grassland": 10,
            "Wetlands": 5,
            "Croplands": 25,
            "Urban/Built-up": 15,
            "Barren": 5,
            "Water": 10,
            "Invalid": 5
        }

        # Create a pie series using class distribution data
        series = QPieSeries()
        for class_id, class_name in class_data.items():
            if class_name in class_distribution:
                series.append(class_name, class_distribution[class_name])

        # Create a chart and add the series
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Class Distribution Pie Chart")

        # Create a chart view to display the chart
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        # Create a dialog to display the chart view
        dialog = QDialog(self)
        dialog.setWindowTitle("Pie Chart")
        dialog.setGeometry(100, 100, 600, 400)
        layout = QVBoxLayout()
        layout.addWidget(chart_view)
        dialog.setLayout(layout)

        # Show the dialog
        dialog.exec_()

    def start_segmentation(self):
        selected_date = self.date_picker.date().toString()
        selected_model = self.model_dropdown.currentText()
        selected_patches = "Sample Patches"  # As an example
        
        print(f"Selected Date: {selected_date}")
        print(f"Selected Model: {selected_model}")
        print(f"Selected Patches: {selected_patches}")
        print("Starting segmentation...")

        # Simulate a segmentation process with progress updates
        for i in range(101):
            self.update_progress_bar(i)  # Update the progress bar
            time.sleep(0.05)  # Simulate some processing time (remove in your actual code)

        print("Segmentation completed!")

    def stop_segmentation(self):
        print("Segmentation stopped!")

    def pause_segmentation(self):
        print("Segmentation paused!")

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)

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
            <!-- ... (HTML code for the map goes here, as in your original code) ... -->
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

