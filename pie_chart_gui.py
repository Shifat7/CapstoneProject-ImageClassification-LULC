from PyQt5.QtWidgets import QVBoxLayout, QWidget, QSizePolicy, QLabel, QHBoxLayout, QFrame, QGraphicsDropShadowEffect
from PyQt5.QtChart import QChart, QChartView, QPieSeries, QLegend
from PyQt5.QtGui import QPainter, QPixmap, QColor
from PyQt5.QtCore import Qt, QMargins
from PyQt5.QtChart import QPieSlice

class PieChartDemo(QWidget):
    def __init__(self, data):
        super(PieChartDemo, self).__init__()

        self.data = data
        self.colors = ["red", "green", "blue", "yellow", "orange", "purple", "cyan", "magenta", "brown"]
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        self.display_pie_chart(self.data)

    def display_pie_chart(self, data):
        series = QPieSeries()
        legend_data = {}  # Store legend data (label and percentage) for later use
        
        for i, (land_type, percentage) in enumerate(data.items()):
            slice = QPieSlice(f"{land_type}", percentage)
            slice.setLabelVisible(False)  # Hide the percentage label on the pie slice
            slice.setColor(QColor(self.colors[i % len(self.colors)]))
            series.append(slice)
            
            # Store legend data for later use
            legend_data[land_type] = percentage

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Distribution of Land Use")
        chart.legend().setVisible(True)
        chart.setMargins(QMargins(0, 50, 0, 0))
        chart.layout().setContentsMargins(10, 10, 10, 10)
        chart.setBackgroundRoundness(15)

        chart_view = QChartView(chart)
        chart_view.setFixedSize(500, 500)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setStyleSheet("border: solid;")
        self.main_layout.addWidget(chart_view)

        # Add legend widget with percentages
        self.add_legend_widget(legend_data)
        
    def add_legend_widget(self, legend_data):
        legend_widget = QWidget(self)
        legend_widget.setStyleSheet("background-color: white; border-radius: 10px;")
        legend_widget.setFixedSize(500, 25)
        
        legend_layout = QHBoxLayout(legend_widget)  
        legend_layout.setContentsMargins(10, 5, 10, 5)   
        
        for land_type, percentage in legend_data.items():
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)  
            row.setSpacing(5)

            color = QColor(self.colors[len(legend_layout) % len(self.colors)])  # Use a color from the palette
            pixmap = QPixmap(10, 10)
            pixmap.fill(color)

            label_icon = QLabel()
            label_icon.setPixmap(pixmap)
            label_text = QLabel(f"{percentage:.2f}%")  # Include percentage in legend text
            row.addWidget(label_icon)
            row.addWidget(label_text)
            row.setAlignment(Qt.AlignCenter)
            legend_layout.addLayout(row)

        self.main_layout.addWidget(legend_widget)
        print("display chart")
