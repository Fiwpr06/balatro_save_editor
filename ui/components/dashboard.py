from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

class DashboardPanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel("Welcome to Balatro Save Editor")
        title.setStyleSheet("font-size: 28px; color: #f9a826; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        info = QLabel(
            "Load a save file (.jkr) to begin modifying your game.\n"
            "You can edit money, chips, hands, jokers, and more.\n\n"
            "Modifying save files may cause unexpected behavior.\n"
            "The editor automatically creates a backup of the original text."
        )
        info.setStyleSheet("font-size: 16px; color: #a095ad;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        layout.addSpacing(30)
        
        load_btn = QPushButton("Load Save File (save.jkr)")
        load_btn.setProperty("class", "ActionBtn")
        load_btn.setFixedSize(250, 50)
        load_btn.clicked.connect(self.main_window.load_save)
        layout.addWidget(load_btn, alignment=Qt.AlignmentFlag.AlignCenter)