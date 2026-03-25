from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QComboBox,
    QGroupBox,
    QPushButton,
    QScrollArea,
    QFrame,
    QMessageBox,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
)
from PyQt6.QtCore import Qt


class JokersPanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.catalog = None
        self.cards = []
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

        # Area Selection
        area_group = QGroupBox("Target Area")
        area_layout = QHBoxLayout(area_group)
        self.area_combo = QComboBox()
        self.area_combo.addItems(["jokers", "consumeables", "deck", "hand"])
        self.area_combo.currentTextChanged.connect(self.refresh_data)
        area_layout.addWidget(QLabel("Select Area: "))
        area_layout.addWidget(self.area_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        area_layout.addWidget(self.refresh_btn)

        container_layout.addWidget(area_group)

        # Current cards list
        cards_group = QGroupBox("Current Cards")
        cards_layout = QVBoxLayout(cards_group)
        self.card_list = QListWidget()
        self.card_list.currentRowChanged.connect(self.on_card_selected)
        cards_layout.addWidget(self.card_list)
        container_layout.addWidget(cards_group)

        # Modifiers
        mods_group = QGroupBox("Card Modifiers")
        mods_grid = QGridLayout(mods_group)
        mods_grid.setColumnStretch(1, 1)

        # Editions
        self.edition_combo = QComboBox()
        self.edition_combo.addItem('none')
        mods_grid.addWidget(QLabel("Edition:"), 0, 0)
        mods_grid.addWidget(self.edition_combo, 0, 1)

        # Seals
        self.seal_combo = QComboBox()
        self.seal_combo.addItem('none')
        mods_grid.addWidget(QLabel("Seal:"), 1, 0)
        mods_grid.addWidget(self.seal_combo, 1, 1)

        # Stickers
        self.sticker_checks = {}
        self.sticker_row = QHBoxLayout()
        mods_grid.addWidget(QLabel('Stickers:'), 2, 0)
        mods_grid.addLayout(self.sticker_row, 2, 1)

        self.preview_box = QPlainTextEdit()
        self.preview_box.setReadOnly(True)
        self.preview_box.setMaximumHeight(130)
        mods_grid.addWidget(QLabel('Preview:'), 3, 0)
        mods_grid.addWidget(self.preview_box, 3, 1)

        action_row = QHBoxLayout()
        self.preview_btn = QPushButton('Preview Changes')
        self.preview_btn.clicked.connect(self.preview_changes)
        self.apply_btn = QPushButton('Apply to Selected Card')
        self.apply_btn.setProperty('class', 'ActionBtn')
        self.apply_btn.clicked.connect(self.apply_selected_card_changes)
        action_row.addWidget(self.preview_btn)
        action_row.addWidget(self.apply_btn)
        mods_grid.addLayout(action_row, 4, 0, 1, 2)

        container_layout.addWidget(mods_group)

        # Add Joker (safe mode)
        add_group = QGroupBox('Add Joker (Safe Mode)')
        add_layout = QHBoxLayout(add_group)
        self.add_joker_combo = QComboBox()
        self.add_joker_btn = QPushButton('Add Joker')
        self.add_joker_btn.setProperty('class', 'ActionBtn')
        self.add_joker_btn.clicked.connect(self.add_joker)
        add_layout.addWidget(QLabel('Joker:'))
        add_layout.addWidget(self.add_joker_combo)
        add_layout.addWidget(self.add_joker_btn)
        container_layout.addWidget(add_group)

        container_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def get_context(self):
        if not self.main_window.editor_service:
            QMessageBox.warning(self, "Warning", "Please load a save file first!")
            return None
        return self.main_window.editor_service

    def on_show(self):
        self.refresh_data()

    def _selected_card(self):
        row = self.card_list.currentRow()
        if row < 0 or row >= len(self.cards):
            return None
        return self.cards[row]

    def _target_modifier_payload(self):
        edition = self.edition_combo.currentData()
        seal = self.seal_combo.currentData()
        stickers = {key: checkbox.isChecked() for key, checkbox in self.sticker_checks.items()}
        return {
            'edition': edition,
            'seal': seal,
            'stickers': stickers,
        }

    def _rebuild_sticker_checks(self, sticker_keys):
        while self.sticker_row.count():
            item = self.sticker_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.sticker_checks = {}
        for sticker_key in sticker_keys:
            checkbox = QCheckBox(sticker_key.capitalize())
            self.sticker_checks[sticker_key] = checkbox
            self.sticker_row.addWidget(checkbox)
        self.sticker_row.addStretch()

    def _populate_catalog(self, service):
        self.catalog = service.get_catalog_payload()

        self.edition_combo.clear()
        self.edition_combo.addItem('none', None)
        for edition in self.catalog['editions']:
            label = edition['name']
            if edition.get('extra'):
                label = f"{label} (extra: {edition['extra']})"
            self.edition_combo.addItem(label, edition['type'])

        self.seal_combo.clear()
        self.seal_combo.addItem('none', None)
        for seal in self.catalog['seals']:
            self.seal_combo.addItem(seal, seal)

        self._rebuild_sticker_checks(self.catalog['stickers'])

        self.add_joker_combo.clear()
        for joker in self.catalog['jokers']:
            self.add_joker_combo.addItem(f"{joker['name']} ({joker['id']})", joker['id'])

    def refresh_data(self):
        service = self.get_context()
        if not service:
            return

        self._populate_catalog(service)
        area_name = self.area_combo.currentText()
        try:
            self.cards = service.list_cards(area_name)
        except Exception as error:
            self.cards = []
            self.card_list.clear()
            self.preview_box.setPlainText(f'Failed to read area {area_name}: {error}')
            return

        self.card_list.clear()
        for card in self.cards:
            card_label = f"#{card['index']} - {card['center_name']} [{card['center_id']}]"
            self.card_list.addItem(QListWidgetItem(card_label))

        if self.cards:
            self.card_list.setCurrentRow(0)
        else:
            self.preview_box.setPlainText('No cards found in this area.')

    def on_card_selected(self, _row):
        selected = self._selected_card()
        if not selected:
            return

        current_edition = selected.get('edition')
        edition_index = self.edition_combo.findData(current_edition)
        self.edition_combo.setCurrentIndex(edition_index if edition_index >= 0 else 0)

        current_seal = selected.get('seal')
        seal_index = self.seal_combo.findData(current_seal)
        self.seal_combo.setCurrentIndex(seal_index if seal_index >= 0 else 0)

        for sticker_key, checkbox in self.sticker_checks.items():
            checkbox.setChecked(bool(selected.get('stickers', {}).get(sticker_key, False)))

        self.preview_changes()

    def preview_changes(self):
        service = self.get_context()
        if not service:
            return

        selected = self._selected_card()
        if not selected:
            self.preview_box.setPlainText('Select a card to preview changes.')
            return

        target = self._target_modifier_payload()
        preview = service.get_card_modification_preview(
            self.area_combo.currentText(),
            selected['index'],
            edition=target['edition'],
            seal=target['seal'],
            stickers=target['stickers'],
        )

        validation_errors = service.validate_card_modification(
            self.area_combo.currentText(),
            selected['index'],
            edition=target['edition'],
            seal=target['seal'],
            stickers=target['stickers'],
        )
        is_valid = len(validation_errors) == 0
        status = '✅ valid' if is_valid else f'❌ invalid ({len(validation_errors)} issue(s))'
        reasons = ''
        if validation_errors:
            reasons = '\nReasons:\n' + '\n'.join(f'- {reason}' for reason in validation_errors)

        preview_text = (
            f"Old:\n{preview['old']}\n\n"
            f"New:\n{preview['new']}\n\n"
            f"Validation: {status}{reasons}"
        )
        self.preview_box.setPlainText(preview_text)

    def apply_selected_card_changes(self):
        service = self.get_context()
        if not service:
            return

        selected = self._selected_card()
        if not selected:
            QMessageBox.warning(self, 'Warning', 'Select a card first.')
            return

        target = self._target_modifier_payload()
        try:
            changed = service.apply_card_modifiers(
                self.area_combo.currentText(),
                selected['index'],
                edition=target['edition'],
                seal=target['seal'],
                stickers=target['stickers'],
            )
            QMessageBox.information(self, 'Success', f'Applied {changed} modifier updates.')
            self.refresh_data()
        except Exception as error:
            QMessageBox.critical(self, 'Error', str(error))

    def add_joker(self):
        service = self.get_context()
        if not service:
            return

        center_id = self.add_joker_combo.currentData()
        if not center_id:
            QMessageBox.warning(self, 'Warning', 'Select a Joker center first.')
            return

        try:
            new_key = service.add_joker(center_id)
            QMessageBox.information(self, 'Success', f'Added Joker with key {new_key}.')
            self.area_combo.setCurrentText('jokers')
            self.refresh_data()
        except Exception as error:
            QMessageBox.critical(self, 'Error', str(error))
