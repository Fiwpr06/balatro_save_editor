from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QScrollArea, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt

class GodModePanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        container_layout = QVBoxLayout(container)
        
        title = QLabel("God Mode & Cheats")
        title.setStyleSheet("font-size: 24px; color: #ff4e50; font-weight: bold; margin-bottom: 20px;")
        container_layout.addWidget(title)
        
        grid = QGridLayout()
        grid.setSpacing(15)
        
        cheats = [
            ("Infinite Resources", "Max Money, Cards, etc.", self.on_infinite),
            ("All Negative Jokers", "Makes all jokers negative (+1 slot)", self.on_negative_jokers),
            ("Max All Hands", "Level 100 on all poker hands", self.on_max_hands),
            ("Free Shop", "Sets item costs to 0", self.on_free_shop),
            ("Guaranteed RNG", "100% chance for probability effects", self.on_rng),
            ("Unlock All Vouchers", "In the current run", self.on_unlock_vouchers),
        ]
        
        for i, (name, desc, handler) in enumerate(cheats):
            row = i // 2
            col = i % 2
            
            btn = QPushButton(f"{name}\n({desc})")
            btn.setProperty("class", "GodModeBtn")
            btn.setMinimumHeight(80)
            btn.clicked.connect(handler)
            
            grid.addWidget(btn, row, col)
            
        container_layout.addLayout(grid)
        container_layout.addStretch()
        
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def verify_editor(self):
        if not self.main_window.editor_service:
            QMessageBox.warning(self, "Warning", "Please load a save file first!")
            return False
        return True

    def on_infinite(self):
        if not self.verify_editor(): return
        try:
            self.main_window.editor_service.god_infinite_everything()
            QMessageBox.information(self, "Success", "Infinite resources applied!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def on_negative_jokers(self):
        if not self.verify_editor(): return
        try:
            acted = self.main_window.editor_service.god_all_negative_jokers()
            QMessageBox.information(self, "Success", f"Applied negative edition to {acted} jokers.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def on_max_hands(self):
        if not self.verify_editor(): return
        try:
            acted = self.main_window.editor_service.god_max_all_hands()
            QMessageBox.information(self, "Success", f"Maxed out {acted} poker hands.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def on_free_shop(self):
        if not self.verify_editor(): return
        try:
            self.main_window.editor_service.god_free_shop()
            QMessageBox.information(self, "Success", "Shop items are now free!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def on_rng(self):
        if not self.verify_editor(): return
        try:
            self.main_window.editor_service.god_guaranteed_rng()
            QMessageBox.information(self, "Success", "100% RNG triggers applied!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def on_unlock_vouchers(self):
        if not self.verify_editor(): return
        try:
            acted = self.main_window.editor_service.unlock_all_vouchers()
            QMessageBox.information(self, "Success", f"Unlocked {acted} vouchers.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
