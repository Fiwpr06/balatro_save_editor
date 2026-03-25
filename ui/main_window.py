import os
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QStackedWidget,
    QFileDialog,
    QMessageBox,
    QFrame,
)
from PyQt6.QtCore import Qt

from services.editor_service import EditorService

from ui.components.dashboard import DashboardPanel
from ui.components.stats_panel import StatsPanel
from ui.components.jokers_panel import JokersPanel
from ui.components.god_mode_panel import GodModePanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Balatro Save Editor - Data Driven")
        self.resize(1240, 820)

        self.editor_service = None

        self.init_ui()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.create_sidebar()

        self.right_container = QWidget()
        self.right_container.setObjectName('MainSurface')
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(14, 14, 14, 14)
        self.right_layout.setSpacing(10)

        self.create_top_bar()

        self.status_label = QLabel('Ready')
        self.status_label.setObjectName('StatusLabel')
        self.right_layout.addWidget(self.status_label)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName('MainContent')
        self.init_panels()
        self.right_layout.addWidget(self.content_stack)

        self.main_layout.addWidget(self.sidebar_widget, 0)
        self.main_layout.addWidget(self.right_container, 1)

    def create_sidebar(self):
        self.sidebar_widget = QFrame()
        self.sidebar_widget.setObjectName("Sidebar")
        self.sidebar_widget.setFixedWidth(260)
        self.sidebar_layout = QVBoxLayout(self.sidebar_widget)
        self.sidebar_layout.setContentsMargins(14, 18, 14, 14)
        self.sidebar_layout.setSpacing(8)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("BALATRO\nSAVE EDITOR")
        title.setObjectName("AppTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.sidebar_layout.addWidget(title)
        subtitle = QLabel("Python GUI • Backend preserved")
        subtitle.setObjectName('SidebarSubtitle')
        self.sidebar_layout.addWidget(subtitle)
        self.sidebar_layout.addSpacing(18)

        self.nav_buttons = {}

        nav_items = [
            ("dashboard", "Dashboard"),
            ("stats", "Player Stats"),
            ("jokers", "Joker Editor"),
            ("god_mode", "God Mode")
        ]

        for idx, (target, label) in enumerate(nav_items):
            btn = QPushButton(label)
            btn.setObjectName(f"Nav_{target}")
            btn.setProperty("nav", "true")
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)

            btn.clicked.connect(lambda checked, t=target, b=btn: self.navigate_to(t, b))
            self.sidebar_layout.addWidget(btn)
            self.nav_buttons[target] = btn

        self.sidebar_layout.addStretch()

    def create_top_bar(self):
        self.top_bar = QFrame()
        self.top_bar.setObjectName("TopBar")
        self.top_bar.setFixedHeight(72)

        layout = QHBoxLayout(self.top_bar)
        layout.setContentsMargins(16, 0, 16, 0)

        left_block = QVBoxLayout()
        header = QLabel('Current Save')
        header.setObjectName('TopBarHeader')
        left_block.addWidget(header)

        self.file_label = QLabel("No save file loaded")
        self.file_label.setObjectName('FileLabel')
        left_block.addWidget(self.file_label)
        layout.addLayout(left_block)

        layout.addStretch()

        load_btn = QPushButton("Load Save")
        load_btn.setObjectName('LoadBtn')
        load_btn.clicked.connect(self.load_save)
        layout.addWidget(load_btn)

        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setObjectName('SaveBtn')
        self.save_btn.clicked.connect(self.save_changes)
        self.save_btn.setEnabled(False)
        layout.addWidget(self.save_btn)

        self.right_layout.addWidget(self.top_bar)

    def init_panels(self):
        self.panels = {}
        
        self.panels["dashboard"] = DashboardPanel(self)
        self.panels["stats"] = StatsPanel(self)
        self.panels["jokers"] = JokersPanel(self)
        self.panels["god_mode"] = GodModePanel(self)
        
        for key, panel in self.panels.items():
            self.content_stack.addWidget(panel)
            
        self.navigate_to("dashboard", self.nav_buttons["dashboard"])

    def navigate_to(self, target, button):
        for btn in self.nav_buttons.values():
            if btn != button:
                btn.setChecked(False)
        button.setChecked(True)

        if target in self.panels:
            self.content_stack.setCurrentWidget(self.panels[target])
            if hasattr(self, 'status_label'):
                self.status_label.setText(f'View: {target}')
            if hasattr(self.panels[target], 'on_show'):
                self.panels[target].on_show()

    def get_default_save_path(self):
        appdata = os.getenv('APPDATA')
        if not appdata:
            return ""
        return os.path.join(appdata, 'Balatro', '2', 'save.jkr')

    def _pick_save_file(self):
        default_save = self.get_default_save_path()
        default_dir = os.path.dirname(default_save) if default_save else os.getcwd()

        dialog = QFileDialog(self, "Open Balatro Save")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilters(["Balatro Save (*.jkr)", "All Files (*)"])
        dialog.setDirectory(default_dir)
        if default_save:
            dialog.selectFile(default_save)

        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)

        if dialog.exec():
            selected = dialog.selectedFiles()
            if selected:
                return selected[0]
        return None

    def load_save(self):
        file_path = self._pick_save_file()

        if file_path:
            try:
                self.editor_service = EditorService(file_path)
                self.file_label.setText(file_path)
                self.save_btn.setEnabled(True)
                self.status_label.setText('Save loaded successfully')

                for panel in self.panels.values():
                    if hasattr(panel, 'refresh_data'):
                        panel.refresh_data()

                QMessageBox.information(self, "Success", "Save file loaded successfully!")

                if self.content_stack.currentWidget() == self.panels["dashboard"]:
                    self.navigate_to("stats", self.nav_buttons["stats"])

            except Exception as e:
                self.status_label.setText('Load failed')
                QMessageBox.critical(self, "Error", f"Failed to load save file:\n{str(e)}")

    def save_changes(self):
        if not self.editor_service:
            return

        try:
            for panel in self.panels.values():
                if hasattr(panel, 'apply_changes'):
                    panel.apply_changes()

            self.editor_service.save()
            self.status_label.setText('Changes saved successfully')
            QMessageBox.information(self, "Success", "Changes saved successfully!")
        except ValueError as e:
            self.status_label.setText('Save blocked by validation')
            QMessageBox.warning(self, "Validation Error", str(e))
        except Exception as e:
            self.status_label.setText('Save failed')
            QMessageBox.critical(self, "Error", f"Failed to save changes:\n{str(e)}")
