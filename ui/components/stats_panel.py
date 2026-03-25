from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QLabel, QSpinBox, QGroupBox, QPushButton, QScrollArea, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt

class StatsPanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.controls = {}
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        container_layout = QVBoxLayout(container)
        
        # --- Value Editor Group ---
        group = QGroupBox("Currency & Resources")
        grid = QGridLayout()
        group.setLayout(grid)
        
        self.add_spinbox("Money", "money", 0, 999999999, grid, 0, 0)
        self.add_spinbox("Chips", "chips", 0, 999999999, grid, 0, 1)
        self.add_spinbox("Interest Cap", "interest_cap", 0, 999999999, grid, 1, 0)
        self.add_spinbox("Reroll Cost", "reroll_cost", 0, 999999, grid, 1, 1)
        self.add_spinbox("Hands Left", "hands_left", 0, 999, grid, 2, 0)
        self.add_spinbox("Discards Left", "discards_left", 0, 999, grid, 2, 1)
        
        apply_btn = QPushButton("Apply Resource Limits")
        apply_btn.setProperty("class", "ActionBtn")
        apply_btn.clicked.connect(self.apply_resources)
        grid.addWidget(apply_btn, 3, 0, 1, 2)
        
        container_layout.addWidget(group)
        
        # --- Capacity Group ---
        cap_group = QGroupBox("Limits & Constraints")
        cap_grid = QGridLayout()
        cap_group.setLayout(cap_grid)
        
        self.add_spinbox("Hand Size", "hand_size", 1, 100, cap_grid, 0, 0)
        self.add_spinbox("Joker Slots", "joker_slots", 1, 100, cap_grid, 0, 1)
        self.add_spinbox("Consumable Slots", "consumable_slots", 1, 100, cap_grid, 1, 0)
        
        apply_cap_btn = QPushButton("Apply Capacity Limits")
        apply_cap_btn.setProperty("class", "ActionBtn")
        apply_cap_btn.clicked.connect(self.apply_capacities)
        cap_grid.addWidget(apply_cap_btn, 2, 0, 1, 2)
        
        container_layout.addWidget(cap_group)
        container_layout.addStretch()
        
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def add_spinbox(self, label_text, key, min_val, max_val, layout, row, col):
        frame = QFrame()
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 10, 10)
        
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #a095ad; font-weight: bold;")
        
        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setMinimumSize(120, 30)
        
        self.controls[key] = spinbox
        
        frame_layout.addWidget(lbl)
        frame_layout.addWidget(spinbox)
        
        layout.addWidget(frame, row, col)

    def on_show(self):
        self.refresh_data()

    def refresh_data(self):
        if not self.main_window.editor_service:
            # Disable controls if no service
            for ctrl in self.controls.values():
                ctrl.setEnabled(False)
            return
            
        # Enable controls
        for ctrl in self.controls.values():
            ctrl.setEnabled(True)
            
        editor = self.main_window.editor_service
        try:
            # We fetch directly using get_value or raw properties if they exist
            money = self.main_window.editor_service.get_current_money()
            self.controls["money"].setValue(int(money))
            
            chips = self.main_window.editor_service.get_current_chips()
            self.controls["chips"].setValue(int(chips))
            
            # The other values from GAME config
            # get_value expects list of keys like ['GAME', 'interest_cap']
            interest = editor.get_value(['GAME', 'interest_cap'])
            if interest is not None: self.controls["interest_cap"].setValue(int(interest))
                
            reroll = editor.get_value(['GAME', 'current_round', 'reroll_cost'])
            if reroll is not None: self.controls["reroll_cost"].setValue(int(reroll))
                
            hands = editor.get_value(['GAME', 'current_round', 'hands_left'])
            if hands is not None: self.controls["hands_left"].setValue(int(hands))
                
            discards = editor.get_value(['GAME', 'current_round', 'discards_left'])
            if discards is not None: self.controls["discards_left"].setValue(int(discards))
                
            h_size = editor.get_value(['GAME', 'starting_params', 'hand_size'])
            if h_size is not None: self.controls["hand_size"].setValue(int(h_size))
                
            j_slots = editor.get_value(['GAME', 'starting_params', 'joker_slots'])
            if j_slots is not None: self.controls["joker_slots"].setValue(int(j_slots))
                
            c_slots = editor.get_value(['GAME', 'starting_params', 'consumable_slots'])
            if c_slots is not None: self.controls["consumable_slots"].setValue(int(c_slots))
                
        except Exception as e:
            print(e)
            
    def apply_resources(self):
        if not self.main_window.editor_service:
            return
            
        editor = self.main_window.editor_service
        try:
            editor.set_money(self.controls["money"].value())
            # For chips, the editor doesn't have an explicit 'set_chips' only 'edit_chips' which is interactive.
            # But we can simulate or directly use _set_by_path if the facade exposes it.
            # wait, it might be editor.editor.set_chips()? Let's check editor.
            editor.editor._set_by_path(['GAME', 'dollars'], self.controls["money"].value())
            editor.editor._set_by_path(['GAME', 'chips'], self.controls["chips"].value())
            editor.set_interest_cap(self.controls["interest_cap"].value())
            editor.set_reroll_cost(self.controls["reroll_cost"].value())
            editor.set_hands_left(self.controls["hands_left"].value())
            editor.set_discards_left(self.controls["discards_left"].value())
            QMessageBox.information(self, "Updated", "Resources updated successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def apply_capacities(self):
        if not self.main_window.editor_service:
            return
            
        editor = self.main_window.editor_service
        try:
            editor.set_hand_size(self.controls["hand_size"].value())
            editor.set_joker_slots(self.controls["joker_slots"].value())
            editor.set_consumable_slots(self.controls["consumable_slots"].value())
            QMessageBox.information(self, "Updated", "Capacities updated successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
