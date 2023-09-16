import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QComboBox, QFileDialog,
                             QFrame, QDateEdit, QCalendarWidget, QLabel)
from PyQt5.QtGui import QPalette, QColor, QPainter, QBrush, QPixmap
from PyQt5.QtCore import Qt, QDate

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

        
        self.model_dropdown = QComboBox()
        self.model_dropdown.setFocusPolicy(Qt.NoFocus)
        self.model_dropdown.setStyleSheet("background-color: transparent; color: white; font-size: 14px;")
        self.model_dropdown.addItem("Select Model")
        self.model_dropdown.addItem("SwinUnet")
        col1_layout.addWidget(self.model_dropdown)
        
        file_btn = QPushButton("Select Patches")
        file_btn.setStyleSheet("background-color: transparent; color: white; font-size: 14px;")
        file_btn.clicked.connect(self.open_file_dialog)
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

       
        main_layout.setStretch(0, 2)
        main_layout.setStretch(1, 8)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Connecting buttons to their respective slots
        segment_btn.clicked.connect(self.start_segmentation)

    def start_segmentation(self):
        selected_date = self.date_picker.date().toString()
        selected_model = self.model_dropdown.currentText()
        selected_patches = "Sample Patches"  # As an example
        
        print(f"Selected Date: {selected_date}")
        print(f"Selected Model: {selected_model}")
        print(f"Selected Patches: {selected_patches}")
        print("Starting segmentation...")

    def stop_segmentation(self):
        print("Segmentation stopped!")

    def pause_segmentation(self):
        print("Segmentation paused!")

    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File")
        if file_name:
            pixmap = QPixmap(file_name)
            self.image_label.setPixmap(pixmap)
            self.image_label.setScaledContents(True)

app = QApplication(sys.argv)
window = DesktopUI()
window.show()
sys.exit(app.exec_())
