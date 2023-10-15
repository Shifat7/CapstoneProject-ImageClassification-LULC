from PyQt5.QtWidgets import QVBoxLayout, QWidget, QLabel, QHBoxLayout
from PyQt5.QtChart import QChart, QChartView, QPieSeries, QPieSlice
from PyQt5.QtGui import QPainter, QPixmap, QColor
from PyQt5.QtCore import Qt, QMargins, QEasingCurve

class PieChartDemo(QWidget):
    def __init__(self, data, animation_duration=1500):
        super(PieChartDemo, self).__init__()

        self.color_mapping = {
            "Forest": "#2ECC71",
            "Shrubland": "#F39C12",
            "Grassland": "#27AE60",
            "Wetlands": "#3498DB",
            "Croplands": "#F1C40F",
            "Urban/Built-up": "#E74C3C",
            "Barren": "#7F8C8D",
            "Water": "#2980B9",
            "Invalid": "#8E44AD"
        }

        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        
        # Initialize empty series and chart_view
        self.series = QPieSeries()
        self.chart = QChart()
        self.chart.setAnimationOptions(QChart.AllAnimations)
        self.chart.setAnimationDuration(animation_duration) 
        # self.chart.setAnimationEasingCurve(QEasingCurve.InOutQuad)
        self.chart.addSeries(self.series)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setFixedSize(500, 500)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setStyleSheet("border: solid;")
        self.main_layout.addWidget(self.chart_view)

        self.update_data(data)

    def update_data(self, data):
        self.data = data

        
        self.series.clear()

        legend_data = {}  
        
        for i, (land_type, percentage) in enumerate(data.items()):
            slice = QPieSlice(f"{land_type}", percentage)
            slice.setLabelVisible(False)
            slice.setColor(QColor(self.color_mapping[land_type]))
            self.series.append(slice)

            
            legend_data[land_type] = percentage

        
        self.chart.setTitle("Distribution of Land Use")
        self.chart.legend().setVisible(True)
        self.chart.setMargins(QMargins(0, 50, 0, 0))
        self.chart.layout().setContentsMargins(10, 10, 10, 10)
        self.chart.setBackgroundRoundness(15)

        # Clear previous legend widget and add the updated one
        for i in reversed(range(self.main_layout.count())): 
            widget = self.main_layout.itemAt(i).widget()
            if isinstance(widget, QWidget) and widget is not self.chart_view:
                widget.setParent(None)
                widget.deleteLater()

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

            color = QColor(self.color_mapping[land_type])
            pixmap = QPixmap(10, 10)
            pixmap.fill(color)

            label_icon = QLabel()
            label_icon.setPixmap(pixmap)
            label_text = QLabel(f"{percentage:.2f}%")  
            row.addWidget(label_icon)
            row.addWidget(label_text)
            row.setAlignment(Qt.AlignCenter)
            legend_layout.addLayout(row)

        self.main_layout.addWidget(legend_widget)
